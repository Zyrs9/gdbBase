from __future__ import annotations
from urllib.parse import quote_plus

class QueryBuilder:
    def __init__(self) -> None:
        self._parts: list[str] = []

    def add(self, token: str) -> 'QueryBuilder':
        token = token.strip()
        if token:
            self._parts.append(token)
        return self

    def extend(self, tokens: list[str]) -> 'QueryBuilder':
        for t in tokens:
            self.add(t)
        return self

    def clear(self) -> 'QueryBuilder':
        self._parts.clear()
        return self

    def build(self) -> str:
        return " ".join(self._parts).strip()

    def build_google_url(self) -> str:
        return f"https://www.google.com/search?q={quote_plus(self.build())}"
