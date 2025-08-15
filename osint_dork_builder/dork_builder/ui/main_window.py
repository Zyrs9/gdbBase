from __future__ import annotations
from typing import List
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QListWidget, QListWidgetItem, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QMessageBox, QInputDialog, QPlainTextEdit
)
from dork_builder.core.models import DorkCategory
from dork_builder.core.commands import OpenInBrowserCommand, NoopCommand
from .viewmodels import AppViewModel

class MainWindow(QMainWindow):
    def __init__(self, vm: AppViewModel) -> None:
        super().__init__()
        self.setWindowTitle("OSINT Google Dork Builder")
        self.resize(1100, 700)
        self._vm = vm
        self._setup_ui()
        self._wire_vm()
        self._vm.initialize()

    def _setup_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        self.lst_categories = QListWidget()
        self.lst_categories.setSelectionMode(QListWidget.SingleSelection)
        self.btn_add_cat = QPushButton("Add Category")
        self.btn_rename_cat = QPushButton("Rename Category")
        self.btn_del_cat = QPushButton("Delete Category")

        self.lst_dorks = QListWidget()
        self.lst_dorks.setSelectionMode(QListWidget.NoSelection)

        self.txt_preview = QLineEdit()
        self.txt_preview.setReadOnly(True)

        self.btn_copy = QPushButton("Copy Query")
        self.btn_open = QPushButton("Open in Google")
        self.btn_clear = QPushButton("Clear")
        self.btn_add = QPushButton("Add Dork")
        self.btn_delete = QPushButton("Delete Dork")

        right_box = QVBoxLayout()
        right_box.addWidget(QLabel("Query Preview:"))
        right_box.addWidget(self.txt_preview)
        right_box.addWidget(self.btn_copy)
        right_box.addWidget(self.btn_open)
        right_box.addWidget(self.btn_clear)
        right_box.addWidget(self.btn_add)
        right_box.addWidget(self.btn_delete)
        right_box.addStretch(1)

        self.txt_shortcuts = QPlainTextEdit()
        self.txt_shortcuts.setPlainText(
            "Common dork shortcuts:\n"
            "site:example.com  - limit results to a specific site\n"
            "intitle:login     - search page titles\n"
            "inurl:admin       - search in URLs\n"
            "filetype:pdf      - find specific file types\n"
            "\"exact phrase\" - match the exact phrase\n"
            "-exclude          - omit results containing term\n"
            "OR                - combine search terms\n"
            "AND               - require both terms\n"
            "()                - group terms"
        )

        left_box = QVBoxLayout()
        left_box.addWidget(self.lst_categories)
        left_box.addWidget(self.btn_add_cat)
        left_box.addWidget(self.btn_rename_cat)
        left_box.addWidget(self.btn_del_cat)

        top_layout = QHBoxLayout()
        top_layout.addLayout(left_box, 2)
        top_layout.addWidget(self.lst_dorks, 5)
        top_layout.addLayout(right_box, 3)

        layout = QVBoxLayout(central)
        layout.addLayout(top_layout)
        layout.addWidget(self.txt_shortcuts)

        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(self.close)
        self.menuBar().addAction(act_quit)

        self._open_cmd = OpenInBrowserCommand(self._build_url)
        self._noop_cmd = NoopCommand()

        self.lst_categories.currentRowChanged.connect(self._on_category_row_changed)
        self.btn_open.clicked.connect(lambda: self._open_cmd())
        self.btn_copy.clicked.connect(self._on_copy_clicked)
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        self.btn_add.clicked.connect(self._on_add_clicked)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        self.btn_add_cat.clicked.connect(self._on_add_category)
        self.btn_rename_cat.clicked.connect(self._on_rename_category)
        self.btn_del_cat.clicked.connect(self._on_delete_category)
        self.lst_dorks.itemChanged.connect(self._on_dork_item_changed)
        self.lst_dorks.itemDoubleClicked.connect(self._on_edit_dork)

    def _wire_vm(self) -> None:
        self._vm.categories_changed.connect(self._on_categories_changed)
        self._vm.current_category_changed.connect(self._on_current_category_changed)
        self._vm.query_changed.connect(self.txt_preview.setText)
        self._vm.dork_checks_changed.connect(self._on_dork_checks_changed)

    def _build_url(self) -> str:
        from urllib.parse import quote_plus
        q = self.txt_preview.text().strip()
        return f"https://www.google.com/search?q={quote_plus(q)}" if q else ""

    @Slot(list)
    def _on_categories_changed(self, cats: List[DorkCategory]) -> None:
        self.lst_categories.clear()
        for c in cats:
            self.lst_categories.addItem(c.label)
        if cats:
            self.lst_categories.setCurrentRow(0)

    @Slot(object)
    def _on_current_category_changed(self, cat: DorkCategory) -> None:
        self._populate_dorks(cat)
        cats = self._vm.categories()
        idx = next((i for i, c in enumerate(cats) if c.key == cat.key), -1)
        if idx >= 0:
            self.lst_categories.blockSignals(True)
            self.lst_categories.setCurrentRow(idx)
            self.lst_categories.blockSignals(False)

    @Slot(set)
    def _on_dork_checks_changed(self, checked: set[int]) -> None:
        self.lst_dorks.blockSignals(True)
        for i in range(self.lst_dorks.count()):
            it = self.lst_dorks.item(i)
            it.setCheckState(Qt.Checked if i in checked else Qt.Unchecked)
        self.lst_dorks.blockSignals(False)

    def _populate_dorks(self, cat: DorkCategory) -> None:
        self.lst_dorks.blockSignals(True)
        self.lst_dorks.clear()
        for item in cat.items:
            it = QListWidgetItem(item)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked)
            self.lst_dorks.addItem(it)
        self.lst_dorks.blockSignals(False)

    @Slot(int)
    def _on_category_row_changed(self, row: int) -> None:
        cats = self._vm.categories()
        if 0 <= row < len(cats):
            self._vm.set_current_category(cats[row].key)

    @Slot()
    def _on_copy_clicked(self) -> None:
        q = self.txt_preview.text().strip()
        if not q:
            QMessageBox.information(self, "Copy", "Query is empty.")
            return
        QGuiApplication.clipboard().setText(q)
        self.statusBar().showMessage("Copied to clipboard.", 2000)

    @Slot()
    def _on_clear_clicked(self) -> None:
        self.lst_dorks.blockSignals(True)
        for i in range(self.lst_dorks.count()):
            self.lst_dorks.item(i).setCheckState(Qt.Unchecked)
        self.lst_dorks.blockSignals(False)
        for i in range(self.lst_dorks.count()):
            self._vm.set_dork_checked(i, False)

    @Slot("QListWidgetItem*")
    def _on_dork_item_changed(self, item) -> None:
        idx = self.lst_dorks.row(item)
        self._vm.set_dork_checked(idx, item.checkState() == Qt.Checked)

    @Slot()
    def _on_add_clicked(self) -> None:
        text, ok = QInputDialog.getText(self, "Add Dork", "Enter dork:")
        if ok and text.strip():
            self._vm.add_dork(text)

    @Slot()
    def _on_delete_clicked(self) -> None:
        items = [self.lst_dorks.item(i).text() for i in range(self.lst_dorks.count())]
        if not items:
            return
        text, ok = QInputDialog.getItem(
            self, "Delete Dork", "Select dork: ", items, 0, False
        )
        if ok and text:
            index = items.index(text)
            self._vm.delete_dork(index)

    @Slot("QListWidgetItem*")
    def _on_edit_dork(self, item) -> None:
        idx = self.lst_dorks.row(item)
        text, ok = QInputDialog.getText(self, "Edit Dork", "Update dork:", text=item.text())
        if ok and text.strip():
            self._vm.edit_dork(idx, text)

    # ------------------------------------------------------------------
    # Category slots
    # ------------------------------------------------------------------

    @Slot()
    def _on_add_category(self) -> None:
        text, ok = QInputDialog.getText(self, "Add Category", "Enter category name:")
        if ok and text.strip():
            self._vm.add_category(text)

    @Slot()
    def _on_delete_category(self) -> None:
        cats = self._vm.categories()
        if not cats:
            return
        row = self.lst_categories.currentRow()
        if not (0 <= row < len(cats)):
            return
        label = cats[row].label
        ret = QMessageBox.question(self, "Delete Category", f"Delete '{label}'?")
        if ret == QMessageBox.Yes:
            self._vm.delete_category(cats[row].key)

    @Slot()
    def _on_rename_category(self) -> None:
        cats = self._vm.categories()
        row = self.lst_categories.currentRow()
        if not (0 <= row < len(cats)):
            return
        cur = cats[row]
        text, ok = QInputDialog.getText(self, "Rename Category", "New name:", text=cur.label)
        if ok and text.strip():
            self._vm.rename_category(cur.key, text)
