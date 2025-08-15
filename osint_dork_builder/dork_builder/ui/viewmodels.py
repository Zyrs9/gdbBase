from __future__ import annotations
from PySide6.QtCore import QObject, Signal, Slot
from typing import List, Dict, Set
from dork_builder.core.models import DorkCategory
from dork_builder.core.query_builder import QueryBuilder
from dork_builder.core.repository import DorkRepository

class AppViewModel(QObject):
    query_changed = Signal(str)
    categories_changed = Signal(list)
    current_category_changed = Signal(object)  # DorkCategory
    dork_checks_changed = Signal(set)

    def __init__(self, repo: DorkRepository) -> None:
        super().__init__()
        self._repo = repo
        self._categories = repo.load()
        self._cat_by_key: Dict[str, DorkCategory] = {c.key: c for c in self._categories}
        self._current_key: str | None = self._categories[0].key if self._categories else None
        self._checked: Set[int] = set()
        self._builder = QueryBuilder()

    def initialize(self) -> None:
        """Emit initial state signals."""
        self.categories_changed.emit(self._categories)
        if self._current_key:
            self.current_category_changed.emit(self._cat_by_key[self._current_key])

    def _emit_query(self) -> None:
        self.query_changed.emit(self._builder.build())

    @Slot(str)
    def set_current_category(self, key: str) -> None:
        if key and key in self._cat_by_key and key != self._current_key:
            self._current_key = key
            self._checked.clear()
            self._builder.clear()
            self.current_category_changed.emit(self._cat_by_key[key])
            self.dork_checks_changed.emit(set())
            self._emit_query()

    def categories(self) -> List[DorkCategory]:
        return self._categories

    # ------------------------------------------------------------------
    # Category Management
    # ------------------------------------------------------------------

    @Slot(str)
    def add_category(self, label: str) -> None:
        """Create a new category with the given label."""
        label = label.strip()
        if not label:
            return
        key = label.lower().replace(" ", "_")
        if key in self._cat_by_key:
            return
        cat = DorkCategory(key=key, label=label, items=[])
        self._categories.append(cat)
        self._cat_by_key[key] = cat
        self._current_key = key
        self._checked.clear()
        self._builder.clear()
        self._repo.save(self._categories)
        self.categories_changed.emit(self._categories)
        self.current_category_changed.emit(cat)
        self.dork_checks_changed.emit(set())
        self._emit_query()

    @Slot(str)
    def delete_category(self, key: str) -> None:
        """Delete the category by key."""
        if key not in self._cat_by_key:
            return
        cat = self._cat_by_key.pop(key)
        self._categories.remove(cat)
        was_current = self._current_key == key
        if was_current:
            self._current_key = self._categories[0].key if self._categories else None
            self._checked.clear()
            self._builder.clear()
        self._repo.save(self._categories)
        self.categories_changed.emit(self._categories)
        if self._current_key and was_current:
            new_cat = self._cat_by_key[self._current_key]
            self.current_category_changed.emit(new_cat)
            self.dork_checks_changed.emit(set())
            self._emit_query()

    @Slot(str, str)
    def rename_category(self, key: str, label: str) -> None:
        """Rename a category identified by key."""
        if key not in self._cat_by_key:
            return
        label = label.strip()
        if not label:
            return
        new_key = label.lower().replace(" ", "_")
        if new_key != key and new_key in self._cat_by_key:
            return
        cat = self._cat_by_key[key]
        new_cat = DorkCategory(key=new_key, label=label, items=cat.items)
        idx = self._categories.index(cat)
        self._categories[idx] = new_cat
        del self._cat_by_key[key]
        self._cat_by_key[new_key] = new_cat
        if self._current_key == key:
            self._current_key = new_key
            self.current_category_changed.emit(new_cat)
        self._repo.save(self._categories)
        self.categories_changed.emit(self._categories)

    @Slot(int, bool)
    def set_dork_checked(self, index: int, checked: bool) -> None:
        if self._current_key is None:
            return
        cat = self._cat_by_key[self._current_key]
        if not (0 <= index < len(cat.items)):
            return
        if checked:
            self._checked.add(index)
        else:
            self._checked.discard(index)
        self._builder.clear()
        tokens = [cat.items[i] for i in sorted(self._checked)]
        self._builder.extend(tokens)
        self.dork_checks_changed.emit(set(self._checked))
        self._emit_query()

    @Slot(str)
    def add_dork(self, text: str) -> None:
        if self._current_key is None:
            return
        text = text.strip()
        if not text:
            return
        cat = self._cat_by_key[self._current_key]
        cat.items.append(text)
        self._repo.save(self._categories)
        self.current_category_changed.emit(cat)

    @Slot(int, str)
    def edit_dork(self, index: int, text: str) -> None:
        if self._current_key is None:
            return
        cat = self._cat_by_key[self._current_key]
        text = text.strip()
        if not (0 <= index < len(cat.items)) or not text:
            return
        cat.items[index] = text
        if index in self._checked:
            self._builder.clear()
            tokens = [cat.items[i] for i in sorted(self._checked)]
            self._builder.extend(tokens)
            self._emit_query()
        self._repo.save(self._categories)
        self.current_category_changed.emit(cat)

    @Slot(int)
    def delete_dork(self, index: int) -> None:
        if self._current_key is None:
            return
        cat = self._cat_by_key[self._current_key]
        if not (0 <= index < len(cat.items)):
            return
        cat.items.pop(index)
        new_checked: Set[int] = set()
        for i in self._checked:
            if i < index:
                new_checked.add(i)
            elif i > index:
                new_checked.add(i - 1)
        self._checked = new_checked
        self._builder.clear()
        tokens = [cat.items[i] for i in sorted(self._checked)]
        self._builder.extend(tokens)
        self.dork_checks_changed.emit(set(self._checked))
        self._repo.save(self._categories)
        self.current_category_changed.emit(cat)
        self._emit_query()
