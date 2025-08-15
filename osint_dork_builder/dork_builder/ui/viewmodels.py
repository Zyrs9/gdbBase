from __future__ import annotations
from PySide6.QtCore import QObject, Signal, Slot
from typing import List, Dict, Set
from dork_builder.core.models import DorkCategory
from dork_builder.core.query_builder import QueryBuilder

class AppViewModel(QObject):
    query_changed = Signal(str)
    categories_changed = Signal(list)
    current_category_changed = Signal(object)  # DorkCategory
    dork_checks_changed = Signal(set)

    def __init__(self, categories: List[DorkCategory]) -> None:
        super().__init__()
        self._categories = categories
        self._cat_by_key: Dict[str, DorkCategory] = {c.key: c for c in categories}
        self._current_key: str | None = categories[0].key if categories else None
        self._checked: Set[int] = set()
        self._builder = QueryBuilder()
        self.categories_changed.emit(categories)
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
