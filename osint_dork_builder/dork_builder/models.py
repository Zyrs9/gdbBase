from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class DorkCategory:
    key: str
    label: str
    items: List[str] = field(default_factory=list)
    tooltips: Dict[str, str] = field(default_factory=dict)


# Query AST for grouping / NOT
@dataclass(frozen=True)
class Tok:
    text: str


@dataclass(frozen=True)
class Not:
    tok: Tok


@dataclass(frozen=True)
class OrGroup:
    toks: List[Tok]


# Profiles (presets)
@dataclass
class Profile:
    name: str
    category: str               # category key
    checked: List[int]          # indices in category.items
    vars: Dict[str, str] = field(default_factory=dict)
    not_indices: List[int] = field(default_factory=list)
    or_groups: List[List[int]] = field(default_factory=list)
