from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List
from .models import DorkCategory

class DorkRepository:
    def __init__(self, json_path: Path):
        self.json_path = json_path

    def load(self) -> List[DorkCategory]:
        if not self.json_path.exists():
            data: Dict[str, list] = {
                "general": [
                    "site:example.com inurl:login",
                    "intitle:\"index of\" backup"
                ],
                "important_files": [
                    "intitle:\"index of\" \"application.properties\"",
                    "ext:xlsx inurl:database"
                ]
            }
        else:
            with self.json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

        cats: List[DorkCategory] = []
        for key, items in data.items():
            label = key.replace("_"," ").title()
            clean = [x.strip() for x in items if isinstance(x, str) and x.strip()]
            cats.append(DorkCategory(key=key, label=label, items=clean))
        return cats

    def save(self, categories: List[DorkCategory]) -> None:
        data = {c.key: c.items for c in categories}
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        with self.json_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
