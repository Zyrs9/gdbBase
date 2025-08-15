from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication
from dork_builder.config.settings import Settings
from dork_builder.core.repository import DorkRepository
from dork_builder.ui.viewmodels import AppViewModel
from dork_builder.ui.main_window import MainWindow

def main() -> int:
    app = QApplication(sys.argv)
    settings = Settings.from_env()
    repo = DorkRepository(settings.dorks_json_path)
    vm = AppViewModel(repo)
    win = MainWindow(vm, settings.open_in_browser)
    win.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
