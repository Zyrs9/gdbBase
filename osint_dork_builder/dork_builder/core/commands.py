from __future__ import annotations
import webbrowser

class Command:
    def __call__(self) -> None:
        raise NotImplementedError

class OpenInBrowserCommand(Command):
    def __init__(self, url_provider: callable[[], str]) -> None:
        self._url_provider = url_provider

    def __call__(self) -> None:
        url = self._url_provider()
        if url:
            webbrowser.open(url)

class NoopCommand(Command):
    def __call__(self) -> None:
        pass
