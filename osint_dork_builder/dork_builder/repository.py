from __future__ import annotations
from typing import Dict, List, Tuple
from pathlib import Path
import json

from models import DorkCategory, Profile

DEFAULTS: Dict[str, List[str]] = {
    "files": ["ext:pdf", "ext:docx", "ext:xlsx", "ext:txt"],
    "content": ['intitle:"index of"', 'inurl:login', 'site:{domain}'],
    "secrets": ['filetype:env', 'password', '"API Key"', 'inurl:config'],
}

class DorkRepository:
    """Load/save categories and profiles (backward compatible with the old flat JSON)."""
    def __init__(self, json_path: Path) -> None:
        self.json_path = Path(json_path)
        self.categories: List[DorkCategory] = []
        self.profiles: Dict[str, Profile] = {}

    def load(self) -> Tuple[List[DorkCategory], Dict[str, Profile]]:
        data = {}
        if self.json_path.exists():
            try:
                with self.json_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        if not data:
            self.categories = [DorkCategory(k, k.capitalize(), v[:]) for k, v in DEFAULTS.items()]
            self.profiles = {}
            self.save()
            return self.categories, self.profiles

        # legacy (flat) shape
        if "categories" not in data:
            cats = []
            for k, items in (data.items() if isinstance(data, dict) else []):
                if isinstance(items, list):
                    cats.append(DorkCategory(k, k.capitalize(), [str(x) for x in items]))
            self.categories = cats
            self.profiles = {}
            return self.categories, self.profiles

        # new shape
        cats = []
        raw_cats = data.get("categories", {}) or {}
        for key, obj in raw_cats.items():
            label = (obj or {}).get("label") or key.capitalize()
            items = list((obj or {}).get("items") or [])
            tips = dict((obj or {}).get("tooltips") or {})
            cats.append(DorkCategory(str(key), str(label), [str(x) for x in items], tips))
        self.categories = cats

        raw_profiles = data.get("profiles", {}) or {}
        profs: Dict[str, Profile] = {}
        for name, obj in raw_profiles.items():
            if not isinstance(obj, dict):
                continue
            profs[name] = Profile(
                name=name,
                category=str(obj.get("category", "")),
                checked=[int(x) for x in obj.get("checked", [])],
                vars={str(k): str(v) for k, v in (obj.get("vars", {}) or {}).items()},
                not_indices=[int(x) for x in obj.get("not_indices", [])],
                or_groups=[[int(y) for y in g] for g in (obj.get("or_groups", []) or [])],
            )
        self.profiles = profs
        return self.categories, self.profiles

    def save(self) -> None:
        data = {
            "categories": {
                c.key: {
                    "label": c.label,
                    "items": c.items,
                    "tooltips": c.tooltips,
                } for c in self.categories
            },
            "profiles": {
                name: {
                    "category": p.category,
                    "checked": p.checked,
                    "vars": p.vars,
                    "not_indices": p.not_indices,
                    "or_groups": p.or_groups,
                } for name, p in self.profiles.items()
            }
        }
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        with self.json_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_profile(self, p: Profile) -> None:
        self.profiles[p.name] = p
        self.save()

    def delete_profile(self, name: str) -> None:
        if name in self.profiles:
            del self.profiles[name]
            self.save()
