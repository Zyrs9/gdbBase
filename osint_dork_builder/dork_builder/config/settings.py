from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import os


@dataclass(frozen=True)
class Settings:
    """Application configuration values.

    Defaults are chosen to match previous hard coded behaviour but the class
    can now build an instance from a ``settings.json`` file and/or environment
    variables.
    """

    dorks_json_path: Path = Path("boxpiper_google_dorks.json")
    open_in_browser: bool = True

    @classmethod
    def from_file(cls, path: Path | str = Path("settings.json")) -> "Settings":
        """Create ``Settings`` reading values from *path* if it exists.

        Any missing values fall back to the class defaults.
        """

        defaults = cls()
        cfg_path = Path(path)
        if not cfg_path.exists():
            return defaults

        data = json.loads(cfg_path.read_text() or "{}")
        return cls(
            dorks_json_path=Path(
                data.get("dorks_json_path", defaults.dorks_json_path)
            ),
            open_in_browser=data.get("open_in_browser", defaults.open_in_browser),
        )

    @classmethod
    def from_env(cls, path: Path | str = Path("settings.json")) -> "Settings":
        """Create ``Settings`` using environment variables.

        ``DORKS_JSON_PATH`` and ``OPEN_IN_BROWSER`` override values loaded from
        ``settings.json``.  Environment variables are parsed conservatively so
        any unrecognised value falls back to the file/default setting.
        """

        base = cls.from_file(path)
        json_path = os.getenv("DORKS_JSON_PATH")
        open_in_browser = os.getenv("OPEN_IN_BROWSER")

        if json_path:
            dorks_path = Path(json_path)
        else:
            dorks_path = base.dorks_json_path

        if open_in_browser is None:
            open_browser = base.open_in_browser
        else:
            open_browser = open_in_browser.lower() in {"1", "true", "yes", "on"}

        return cls(dorks_json_path=dorks_path, open_in_browser=open_browser)


# Convenience accessor preserving previous ``SETTINGS`` style usage.
SETTINGS = Settings.from_env()

