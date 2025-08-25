from __future__ import annotations
from typing import List, Dict, Set
from PySide6.QtCore import QObject, Signal

from models import DorkCategory, Profile
from query_builder import QueryBuilder

import re
import unicodedata

VAR_RE = re.compile(r"\{([A-Za-z0-9_]+)\}")

def _slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if ch.isalnum() or ch in (" ", "-", "_")).strip().lower()
    s = re.sub(r"\s+", "-", s)
    return s or "category"

class AppViewModel(QObject):
    categoriesChanged = Signal(list)          # List[DorkCategory]
    currentCategoryChanged = Signal(object)   # DorkCategory | None
    queryChanged = Signal(str)
    variablesChanged = Signal(dict)           # Dict[str, str]
    profilesChanged = Signal(list)            # List[str]

    def __init__(self, repo) -> None:
        super().__init__()
        self.repo = repo
        self.categories: List[DorkCategory] = []
        self.current_index: int = -1
        # state per category
        self.checked_by_cat: Dict[str, Set[int]] = {}
        self.not_by_cat: Dict[str, Set[int]] = {}
        self.or_groups_by_cat: Dict[str, List[Set[int]]] = {}
        # variables
        self.vars: Dict[str, str] = {}
        # builder
        self.builder = QueryBuilder()
        # profiles
        self.profiles: Dict[str, Profile] = {}

    # ===================== Load / Current =====================
    def load(self) -> None:
        cats, profs = self.repo.load()
        self.categories = cats
        self.profiles = profs
        if cats:
            self.current_index = 0
        self.categoriesChanged.emit(cats)
        self.currentCategoryChanged.emit(self.current_category())
        self.profilesChanged.emit(sorted(self.profiles.keys()))
        self._rebuild_query()

    def current_category(self) -> DorkCategory | None:
        if 0 <= self.current_index < len(self.categories):
            return self.categories[self.current_index]
        return None

    def set_current_index(self, idx: int) -> None:
        if 0 <= idx < len(self.categories):
            self.current_index = idx
            self.currentCategoryChanged.emit(self.current_category())
            self._rebuild_query()

    # ===================== Selection / Groups / NOT =====================
    def toggle_checked(self, item_index: int) -> None:
        c = self.current_category()
        if not c: return
        s = self.checked_by_cat.setdefault(c.key, set())
        if item_index in s: s.remove(item_index)
        else: s.add(item_index)
        self._rebuild_query()

    def set_checked(self, indices: List[int]) -> None:
        c = self.current_category()
        if not c: return
        self.checked_by_cat[c.key] = set(indices)
        self._rebuild_query()

    def toggle_not(self, item_index: int) -> None:
        c = self.current_category()
        if not c: return
        s = self.not_by_cat.setdefault(c.key, set())
        if item_index in s: s.remove(item_index)
        else: s.add(item_index)
        self._rebuild_query()

    def make_or_group(self, indices: List[int]) -> None:
        """Create/merge OR groups from given indices; auto-check them."""
        c = self.current_category()
        if not c or len(indices) < 2:
            return
        checked = self.checked_by_cat.setdefault(c.key, set())
        checked.update(indices)
        groups = self.or_groups_by_cat.setdefault(c.key, [])
        groups.append(set(indices))
        self._normalize_groups_for_category(c.key)
        self._rebuild_query()

    def clear_groups(self) -> None:
        c = self.current_category()
        if not c: return
        self.or_groups_by_cat[c.key] = []
        self._rebuild_query()

    def _normalize_groups_for_category(self, cat_key: str) -> None:
        """Merge overlapping groups and drop groups with < 2 items."""
        groups = [set(g) for g in self.or_groups_by_cat.get(cat_key, []) if len(g) >= 2]
        changed = True
        while changed:
            changed = False
            merged: List[Set[int]] = []
            for g in groups:
                placed = False
                for r in merged:
                    if not r.isdisjoint(g):
                        r |= g
                        placed = True
                        changed = True
                        break
                if not placed:
                    merged.append(set(g))
            groups = merged
        self.or_groups_by_cat[cat_key] = [g for g in groups if len(g) >= 2]

    # ===================== Variables =====================
    def set_variable(self, name: str, value: str) -> None:
        self.vars[name] = value
        self._rebuild_query(emit_vars=False)

    # ===================== Editing dorks =====================
    def rename_dork(self, item_index: int, new_text: str) -> None:
        c = self.current_category()
        if not c: return
        if not (0 <= item_index < len(c.items)): return
        new_text = (new_text or "").strip()
        if not new_text or c.items[item_index] == new_text:
            return
        c.items[item_index] = new_text
        self.repo.save()
        self._rebuild_query()

    def add_dork(self, text: str) -> None:
        c = self.current_category()
        if not c: return
        text = (text or "").strip()
        if not text:
            return
        c.items.append(text)
        self.repo.save()
        self.currentCategoryChanged.emit(self.current_category())
        self._rebuild_query()

    def delete_dorks(self, indices: List[int]) -> None:
        c = self.current_category()
        if not c or not indices:
            return
        indices_sorted = sorted(set(i for i in indices if 0 <= i < len(c.items)), reverse=True)
        for i in indices_sorted:
            del c.items[i]
        self._reindex_after_removal(c.key, sorted(indices))
        self.repo.save()
        self.currentCategoryChanged.emit(self.current_category())
        self._rebuild_query()

    # ===================== Move dorks between categories =====================
    def move_dorks(self, src_key: str, dst_key: str, indices: List[int]) -> None:
        if src_key == dst_key or not indices:
            return
        src = next((c for c in self.categories if c.key == src_key), None)
        dst = next((c for c in self.categories if c.key == dst_key), None)
        if not src or not dst:
            return

        # collect texts to move
        indices_sorted = sorted(set(i for i in indices if 0 <= i < len(src.items)))
        texts = [src.items[i] for i in indices_sorted]

        # remove from source (descending to keep indices stable while removing)
        for i in reversed(indices_sorted):
            del src.items[i]

        # reindex source selections/groups
        self._reindex_after_removal(src.key, indices_sorted)

        # append to destination (to end)
        dst.items.extend(texts)

        self.repo.save()

        # refresh views
        self.currentCategoryChanged.emit(self.current_category())
        self._rebuild_query()

    def _reindex_after_removal(self, cat_key: str, removed_sorted: List[int]) -> None:
        """After removing some indices from a category, fix checked/not/groups indices."""
        removed = list(removed_sorted)
        def remap_set(s: Set[int]) -> Set[int]:
            out: Set[int] = set()
            for idx in s:
                if idx in removed:
                    continue
                # new index = idx - count(removed < idx)
                shift = 0
                for r in removed:
                    if r < idx:
                        shift += 1
                out.add(idx - shift)
            return out

        if cat_key in self.checked_by_cat:
            self.checked_by_cat[cat_key] = remap_set(self.checked_by_cat[cat_key])
        if cat_key in self.not_by_cat:
            self.not_by_cat[cat_key] = remap_set(self.not_by_cat[cat_key])
        if cat_key in self.or_groups_by_cat:
            new_groups: List[Set[int]] = []
            for g in self.or_groups_by_cat[cat_key]:
                g2 = remap_set(g)
                if len(g2) >= 2:
                    new_groups.append(g2)
            self.or_groups_by_cat[cat_key] = new_groups

    # ===================== Category CRUD =====================
    def create_category(self, name: str) -> None:
        raw = (name or "").strip()
        if not raw: return
        base_key = _slugify(raw)
        key = base_key
        existing = {c.key for c in self.categories}
        i = 2
        while key in existing:
            key = f"{base_key}-{i}"
            i += 1
        cat = DorkCategory(key=key, label=raw, items=[])
        self.categories.append(cat)
        self.checked_by_cat.setdefault(key, set())
        self.not_by_cat.setdefault(key, set())
        self.or_groups_by_cat.setdefault(key, [])
        self.repo.save()
        self.categoriesChanged.emit(self.categories)
        self.current_index = len(self.categories) - 1
        self.currentCategoryChanged.emit(self.current_category())
        self._rebuild_query()

    def delete_current_category(self) -> None:
        if not (0 <= self.current_index < len(self.categories)):
            return
        key = self.categories[self.current_index].key
        # remove category
        del self.categories[self.current_index]
        # cleanup state
        self.checked_by_cat.pop(key, None)
        self.not_by_cat.pop(key, None)
        self.or_groups_by_cat.pop(key, None)
        # fix current index
        if self.current_index >= len(self.categories):
            self.current_index = len(self.categories) - 1
        self.repo.save()
        self.categoriesChanged.emit(self.categories)
        self.currentCategoryChanged.emit(self.current_category())
        self._rebuild_query()

    def rename_current_category(self, new_name: str) -> None:
        if not (0 <= self.current_index < len(self.categories)):
            return
        c = self.categories[self.current_index]
        new_label = (new_name or "").strip()
        if not new_label:
            return
        old_key = c.key
        # compute new key (stable if same label ignoring case/space)
        base_key = _slugify(new_label)
        if base_key != old_key:
            key = base_key
            existing = {cat.key for cat in self.categories if cat.key != old_key}
            i = 2
            while key in existing:
                key = f"{base_key}-{i}"
                i += 1
            # re-key maps
            self.checked_by_cat[key] = self.checked_by_cat.pop(old_key, set())
            self.not_by_cat[key] = self.not_by_cat.pop(old_key, set())
            self.or_groups_by_cat[key] = self.or_groups_by_cat.pop(old_key, [])
            c.key = key
        c.label = new_label
        self.repo.save()
        self.categoriesChanged.emit(self.categories)
        self.currentCategoryChanged.emit(self.current_category())
        self._rebuild_query()

    # ===================== Build =====================
    def _collect_placeholders(self, texts: List[str]) -> List[str]:
        names: Set[str] = set()
        for t in texts:
            for m in VAR_RE.finditer(t):
                names.add(m.group(1))
        return sorted(names)

    def _rebuild_query(self, emit_vars: bool = True) -> None:
        c = self.current_category()
        self.builder.clear()
        if not c:
            self.queryChanged.emit("")
            if emit_vars:
                self.variablesChanged.emit({})
            return

        checked = sorted(self.checked_by_cat.get(c.key, set()))
        nots = set(self.not_by_cat.get(c.key, set()))
        groups = [set(g) for g in self.or_groups_by_cat.get(c.key, [])]

        used: Set[int] = set()
        for g in groups:
            included = sorted(g & set(checked))
            if len(included) >= 2:
                texts = [c.items[i] for i in included]
                self.builder.add_or_group(texts)
                used |= set(included)

        for i in checked:
            if i in used: continue
            text = c.items[i]
            if i in nots: self.builder.add_not(text)
            else: self.builder.add(text)

        self.builder.set_vars(self.vars)

        used_texts = []
        for i in checked:
            if i in used: continue
            used_texts.append(c.items[i])
        for g in groups:
            included = sorted(g & set(checked))
            if len(included) >= 2:
                used_texts.extend([c.items[i] for i in included])

        var_names = self._collect_placeholders(used_texts)
        if emit_vars:
            missing = {k: "" for k in var_names if k not in self.vars}
            if missing:
                self.vars.update(missing)
            self.variablesChanged.emit({k: self.vars.get(k, "") for k in var_names})

        self.queryChanged.emit(self.builder.build())

    # ===================== Profiles =====================
    def save_profile(self, name: str) -> None:
        c = self.current_category()
        if not c: return
        p = Profile(
            name=name,
            category=c.key,
            checked=sorted(self.checked_by_cat.get(c.key, set())),
            vars=dict(self.vars),
            not_indices=sorted(self.not_by_cat.get(c.key, set())),
            or_groups=[sorted(list(g)) for g in self.or_groups_by_cat.get(c.key, [])],
        )
        self.repo.save_profile(p)
        self.profiles[name] = p
        self.profilesChanged.emit(sorted(self.profiles.keys()))

    def apply_profile(self, name: str) -> None:
        p = self.profiles.get(name)
        if not p: return
        for idx, cat in enumerate(self.categories):
            if cat.key == p.category:
                self.current_index = idx
                break
        self.checked_by_cat[p.category] = set(p.checked)
        self.not_by_cat[p.category] = set(p.not_indices or [])
        self.or_groups_by_cat[p.category] = [set(g) for g in (p.or_groups or [])]
        self.vars = dict(p.vars or {})
        self.currentCategoryChanged.emit(self.current_category())
        self._rebuild_query()

    def delete_profile(self, name: str) -> None:
        self.repo.delete_profile(name)
        self.profiles.pop(name, None)
        self.profilesChanged.emit(sorted(self.profiles.keys()))
