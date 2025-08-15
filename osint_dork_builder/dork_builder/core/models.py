from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

@dataclass(frozen=True)
class DorkCategory:
    key: str
    label: str
    items: List[str] = field(default_factory=list)
