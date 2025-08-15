from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Settings:
    dorks_json_path: Path = Path("boxpiper_google_dorks.json")
    open_in_browser: bool = True

SETTINGS = Settings()
