from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import os


@dataclass(frozen=True)
class Settings:
    """Configuration with env/file overrides.

    Env:
      - DORKS_JSON_PATH
      - OPEN_IN_BROWSER  (1/true/yes/on)
    Optional settings.json can live in CWD or next to this file.
    """
    dorks_json_path: Path = Path("dorks.json")
    open_in_browser: bool = True

    @staticmethod
    def _load_json_settings() -> dict:
        candidates = [
            Path.cwd() / "settings.json",
            Path(__file__).resolve().parent / "settings.json",
        ]
        for p in candidates:
            if p.exists():
                try:
                    with p.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        return data
                except Exception:
                    return {}
        return {}

    @classmethod
    def from_env(cls) -> "Settings":
        base = cls(**cls._load_json_settings())

        dorks_env = os.environ.get("DORKS_JSON_PATH")
        open_env = os.environ.get("OPEN_IN_BROWSER")

        dorks_path = Path(dorks_env) if dorks_env else Path(base.dorks_json_path)
        if open_env is None:
            open_browser = bool(base.open_in_browser)
        else:
            open_browser = open_env.strip().lower() in {"1", "true", "yes", "on"}

        return cls(dorks_json_path=dorks_path, open_in_browser=open_browser)


SETTINGS = Settings.from_env()
