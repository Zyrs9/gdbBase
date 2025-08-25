from __future__ import annotations
from typing import Protocol, Callable
import webbrowser


class Command(Protocol):
    def __call__(self) -> None: ...


def open_url_provider(url_getter: Callable[[], str]) -> Command:
    def cmd() -> None:
        url = url_getter()
        if url:
            try:
                webbrowser.open(url)
            except Exception:
                pass
    return cmd


def noop() -> None:
    return None
