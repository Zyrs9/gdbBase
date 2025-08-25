from __future__ import annotations
from urllib.parse import quote_plus
from typing import List, Dict, Iterable, Union
import re

from models import Tok, Not, OrGroup

Part = Union[Tok, Not, OrGroup]
_VAR_RE = re.compile(r"\{([A-Za-z0-9_]+)\}")

class QueryBuilder:
    """Build a search query with variables, OR groups, and NOTs."""
    def __init__(self) -> None:
        self.parts: List[Part] = []
        self.vars: Dict[str, str] = {}

    def clear(self) -> None:
        self.parts.clear()

    def set_vars(self, mapping: Dict[str, str] | None) -> None:
        self.vars = dict(mapping or {})

    def add(self, text: str) -> None:
        self.parts.append(Tok(text))

    def add_not(self, text: str) -> None:
        self.parts.append(Not(Tok(text)))

    def add_or_group(self, texts: Iterable[str]) -> None:
        toks = [Tok(t) for t in texts if str(t).strip()]
        if toks:
            self.parts.append(OrGroup(toks))

    def _subst(self, s: str) -> str:
        def _repl(m: re.Match) -> str:
            key = m.group(1)
            return self.vars.get(key, m.group(0))
        return _VAR_RE.sub(_repl, s)

    def build(self) -> str:
        out: List[str] = []
        for p in self.parts:
            if isinstance(p, Tok):
                out.append(self._subst(p.text))
            elif isinstance(p, Not):
                out.append("-" + self._subst(p.tok.text))
            else:  # OrGroup
                out.append("(" + " OR ".join(self._subst(t.text) for t in p.toks) + ")")
        return " ".join(filter(None, (s.strip() for s in out)))

    def to_google_url(self) -> str:
        return f"https://www.google.com/search?q={quote_plus(self.build())}"
