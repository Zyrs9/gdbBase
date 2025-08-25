from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication

from settings import SETTINGS
from repository import DorkRepository
from viewmodels import AppViewModel
from main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    repo = DorkRepository(SETTINGS.dorks_json_path)
    vm = AppViewModel(repo)
    win = MainWindow(vm)
    vm.load()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
