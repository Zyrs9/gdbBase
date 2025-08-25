from __future__ import annotations
from typing import Dict, List, Set

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QPushButton, QPlainTextEdit,
    QLineEdit, QFormLayout, QGroupBox, QSplitter, QInputDialog, QMessageBox,
    QMenu, QToolBar, QComboBox, QToolBox
)
from PySide6.QtCore import Qt, QSize, QMimeData, QPoint
from PySide6.QtGui import QClipboard, QAction, QColor, QBrush, QDrag

from models import DorkCategory
from viewmodels import AppViewModel
from commands import open_url_provider, noop
from settings import SETTINGS

# ---- Drag & Drop MIME type ----
MIME_MOVE = "application/x-dorks-move"  # payload: "src_key|idx1,idx2,idx3"

# Colors
BRUSH_OR = QBrush(QColor("#FFF3BF"))   # OR group bg
BRUSH_NOT = QBrush(QColor("#D32F2F"))  # NOT fg
BRUSH_TEXT = QBrush(QColor("#000000")) # normal fg
BRUSH_BG = QBrush()                    # default bg


# ===================== Custom Widgets for DnD =====================
class DorksListWidget(QListWidget):
    def __init__(self, get_src_key_callable):
        super().__init__()
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragOnly)
        self._get_src_key = get_src_key_callable

    def startDrag(self, supportedActions):
        # gather selected indices
        rows = sorted({i.row() for i in self.selectedIndexes()})
        if not rows:
            return
        src_key = self._get_src_key() or ""
        md = QMimeData()
        md.setData(MIME_MOVE, f"{src_key}|{','.join(map(str, rows))}".encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(md)
        drag.exec(Qt.MoveAction)


class CategoriesListWidget(QListWidget):
    def __init__(self, on_drop_callable):
        super().__init__()
        self.on_drop = on_drop_callable
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME_MOVE):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME_MOVE):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        if not e.mimeData().hasFormat(MIME_MOVE):
            e.ignore()
            return
        payload = bytes(e.mimeData().data(MIME_MOVE)).decode("utf-8")
        # find destination category by drop position
        pos: QPoint = e.position().toPoint() if hasattr(e, "position") else e.pos()
        item = self.itemAt(pos)
        if item is None:
            e.ignore()
            return
        dest_row = self.row(item)
        self.on_drop(payload, dest_row)
        e.acceptProposedAction()


# ===================== Main Window =====================
class MainWindow(QMainWindow):
    def __init__(self, vm: AppViewModel) -> None:
        super().__init__()
        self.vm = vm
        self.setWindowTitle("Dork Builder")
        self.resize(1120, 700)

        # -- Left: categories (with toolbar)
        self.lst_categories = CategoriesListWidget(self._handle_drop_to_category)
        self.lst_categories.setMinimumWidth(260)
        self.lst_categories.currentRowChanged.connect(self.vm.set_current_index)

        self.btn_add_cat = QPushButton("Yeni Kategori")
        self.btn_ren_cat = QPushButton("Yeniden Adlandır")
        self.btn_del_cat = QPushButton("Sil")

        self.btn_add_cat.clicked.connect(self._create_category)
        self.btn_ren_cat.clicked.connect(self._rename_category)
        self.btn_del_cat.clicked.connect(self._delete_category)

        # context menu for categories
        self.lst_categories.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lst_categories.customContextMenuRequested.connect(self._open_category_menu)

        cat_box = QVBoxLayout()
        cat_box.addWidget(QLabel("Kategoriler"))
        cat_box.addWidget(self.lst_categories, 1)
        cat_btns = QHBoxLayout()
        cat_btns.addWidget(self.btn_add_cat)
        cat_btns.addWidget(self.btn_ren_cat)
        cat_btns.addWidget(self.btn_del_cat)
        cat_box.addLayout(cat_btns)
        left = QWidget(); left.setLayout(cat_box)

        # -- Middle: dorks (editable, drag source)
        self.lst_dorks = DorksListWidget(lambda: self._current_cat_key())
        self.lst_dorks.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lst_dorks.customContextMenuRequested.connect(self._open_dork_menu)
        self.lst_dorks.itemChanged.connect(self._on_item_changed)

        # Dork ekleme/silme butonları
        self.btn_add_dork = QPushButton("Dork Ekle")
        self.btn_del_dork = QPushButton("Dork Sil")
        self.btn_add_dork.clicked.connect(self._add_dork)
        self.btn_del_dork.clicked.connect(self._delete_dork)

        mid = QWidget(); mv = QVBoxLayout(mid)
        mv.addWidget(QLabel("Dorks"))
        mv.addWidget(self.lst_dorks, 1)
        dork_btns = QHBoxLayout()
        dork_btns.addWidget(self.btn_add_dork)
        dork_btns.addWidget(self.btn_del_dork)
        mv.addLayout(dork_btns)

        # -- Right: QToolBox (collapsible menus)
        self.toolbox = QToolBox()

        # Page 1: Query
        query_page = QWidget(); ql = QVBoxLayout(query_page)
        self.txt_query = QPlainTextEdit(); self.txt_query.setReadOnly(True)
        self.btn_copy = QPushButton("Kopyala")
        self.btn_open = QPushButton("Google'da Aç")
        self.btn_clear = QPushButton("Seçimleri Temizle")
        self.btn_copy.clicked.connect(self._copy_query)
        self.btn_clear.clicked.connect(self._clear_checks)
        if SETTINGS.open_in_browser:
            self.btn_open.clicked.connect(open_url_provider(lambda: self.vm.builder.to_google_url()))
        else:
            self.btn_open.clicked.connect(noop)
        ql.addWidget(QLabel("Query Preview"))
        ql.addWidget(self.txt_query, 1)
        qa = QHBoxLayout()
        qa.addWidget(self.btn_copy)
        qa.addWidget(self.btn_open)
        qa.addWidget(self.btn_clear)
        ql.addLayout(qa)
        self.toolbox.addItem(query_page, "Query")

        # Page 2: Variables
        vars_page = QWidget(); vl = QVBoxLayout(vars_page)
        self.vars_group = QGroupBox("Variables")
        self.vars_form = QFormLayout(); self.vars_group.setLayout(self.vars_form)
        vl.addWidget(self.vars_group)
        self.toolbox.addItem(vars_page, "Variables")

        # Page 3: Profiles
        prof_page = QWidget(); pl = QVBoxLayout(prof_page)
        row = QHBoxLayout()
        self.cmb_profiles = QComboBox(); self.cmb_profiles.setMinimumWidth(200)
        self.btn_save_profile = QPushButton("Profili Kaydet")
        self.btn_delete_profile = QPushButton("Profili Sil")
        self.btn_save_profile.clicked.connect(self._save_profile)
        self.btn_delete_profile.clicked.connect(self._delete_profile)
        self.cmb_profiles.activated.connect(self._profile_activated)  # int overload
        row.addWidget(QLabel("Profile:")); row.addWidget(self.cmb_profiles, 1)
        row.addWidget(self.btn_save_profile); row.addWidget(self.btn_delete_profile)
        pl.addLayout(row)
        self.toolbox.addItem(prof_page, "Profiles")

        # -- Overall layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(mid)
        right = QWidget(); rv = QVBoxLayout(right); rv.addWidget(self.toolbox)
        splitter.addWidget(right)

        center = QWidget(); lay = QHBoxLayout(center); lay.addWidget(splitter)
        self.setCentralWidget(center)

        # Toolbar (group/not)
        tb = QToolBar("Shortcuts"); tb.setIconSize(QSize(16, 16)); self.addToolBar(tb)
        act_group_or = QAction("Group OR", self)
        act_toggle_not = QAction("Toggle NOT", self)
        act_ungroup = QAction("Grupları Temizle", self)
        act_group_or.triggered.connect(self._group_or_selected)
        act_toggle_not.triggered.connect(self._toggle_not_selected)
        act_ungroup.triggered.connect(self.vm.clear_groups)
        tb.addAction(act_group_or); tb.addAction(act_toggle_not); tb.addAction(act_ungroup)

        # VM bindings
        self.vm.categoriesChanged.connect(self._load_categories)
        self.vm.currentCategoryChanged.connect(self._load_dorks_for_category)
        self.vm.queryChanged.connect(self.txt_query.setPlainText)
        self.vm.variablesChanged.connect(self._render_vars)
        self.vm.profilesChanged.connect(self._load_profiles)

    # ===================== Helpers =====================
    def _current_cat_key(self) -> str:
        c = self.vm.current_category()
        return c.key if c else ""

    # ===================== VM handlers =====================
    def _load_categories(self, cats: List[DorkCategory]) -> None:
        self.lst_categories.blockSignals(True)
        try:
            self.lst_categories.clear()
            for c in cats:
                self.lst_categories.addItem(c.label)
            if cats:
                self.lst_categories.setCurrentRow(self.vm.current_index)
        finally:
            self.lst_categories.blockSignals(False)

    def _load_dorks_for_category(self, cat: DorkCategory | None) -> None:
        self.lst_dorks.blockSignals(True)
        try:
            self.lst_dorks.clear()
            if not cat:
                return
            checked = self.vm.checked_by_cat.get(cat.key, set())
            for i, text in enumerate(cat.items):
                item = QListWidgetItem(text)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
                item.setCheckState(Qt.Checked if i in checked else Qt.Unchecked)
                self.lst_dorks.addItem(item)
            self._apply_item_styles(cat)
        finally:
            self.lst_dorks.blockSignals(False)

    def _apply_item_styles(self, cat: DorkCategory) -> None:
        nots: Set[int] = self.vm.not_by_cat.get(cat.key, set())
        groups = [set(g) for g in self.vm.or_groups_by_cat.get(cat.key, [])]
        in_any_group: Set[int] = set().union(*groups) if groups else set()
        for i in range(self.lst_dorks.count()):
            it = self.lst_dorks.item(i)
            it.setForeground(BRUSH_NOT if i in nots else BRUSH_TEXT)
            it.setBackground(BRUSH_OR if i in in_any_group else BRUSH_BG)

    # ===================== Right panel rendering =====================
    def _render_vars(self, mapping: Dict[str, str]) -> None:
        while self.vars_form.rowCount():
            self.vars_form.removeRow(0)
        if not mapping:
            self.vars_group.setVisible(False)
            return
        self.vars_group.setVisible(True)
        for name, val in mapping.items():
            edit = QLineEdit(val)
            # Her değişiklikte ViewModel'e aktar
            def make_handler(nm: str, e: QLineEdit = edit):
                def h():
                    self.vm.set_variable(nm, e.text())
                return h
            edit.textChanged.connect(make_handler(name))
            self.vars_form.addRow(QLabel(name), edit)

    def _load_profiles(self, names: List[str]) -> None:
        self.cmb_profiles.blockSignals(True)
        try:
            self.cmb_profiles.clear()
            self.cmb_profiles.addItems(sorted(names))
        finally:
            self.cmb_profiles.blockSignals(False)

    # ===================== DnD between lists =====================
    def _handle_drop_to_category(self, payload: str, dest_row: int) -> None:
        """payload = 'src_key|idx1,idx2,...' dropped onto category at dest_row."""
        parts = payload.split("|", 1)
        if len(parts) != 2:
            return
        src_key, idx_csv = parts
        if not (0 <= dest_row < len(self.vm.categories)):
            return
        dst_key = self.vm.categories[dest_row].key
        if not idx_csv.strip():
            return
        indices = [int(x) for x in idx_csv.split(",") if x.strip().isdigit()]
        self.vm.move_dorks(src_key, dst_key, indices)
        # refresh both lists
        self._load_categories(self.vm.categories)
        self._load_dorks_for_category(self.vm.current_category())

    # ===================== UI actions =====================
    def _profile_activated(self, index: int) -> None:
        if index < 0: return
        name = self.cmb_profiles.itemText(index).strip()
        if name:
            self.vm.apply_profile(name)

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        cat = self.vm.current_category()
        if not cat:
            return
        # checked set
        checked: List[int] = []
        for i in range(self.lst_dorks.count()):
            it = self.lst_dorks.item(i)
            if it.checkState() == Qt.Checked:
                checked.append(i)
        self.vm.set_checked(checked)
        # persist edits
        for i in range(self.lst_dorks.count()):
            it = self.lst_dorks.item(i)
            txt = it.text()
            if txt != cat.items[i]:
                self.vm.rename_dork(i, txt)
        self._apply_item_styles(cat)

    def _copy_query(self) -> None:
        QApplication.clipboard().setText(self.vm.builder.build(), mode=QClipboard.Clipboard)

    def _clear_checks(self) -> None:
        cat = self.vm.current_category()
        if not cat:
            return
        self.vm.set_checked([])
        self._load_dorks_for_category(cat)

    def _open_dork_menu(self, pos) -> None:
        menu = QMenu(self)
        act_group = menu.addAction("Group with OR")
        act_not = menu.addAction("Toggle NOT")
        act_ungroup = menu.addAction("Grupları Temizle")
        action = menu.exec(self.lst_dorks.mapToGlobal(pos))
        if not action:
            return
        if action == act_group:
            self._group_or_selected()
        elif action == act_not:
            self._toggle_not_selected()
        elif action == act_ungroup:
            self.vm.clear_groups()
            cat = self.vm.current_category()
            if cat:
                self._apply_item_styles(cat)

    def _open_category_menu(self, pos) -> None:
        menu = QMenu(self)
        act_new = menu.addAction("Yeni Kategori")
        act_ren = menu.addAction("Yeniden Adlandır")
        act_del = menu.addAction("Sil")
        action = menu.exec(self.lst_categories.mapToGlobal(pos))
        if not action:
            return
        if action == act_new:
            self._create_category()
        elif action == act_ren:
            self._rename_category()
        elif action == act_del:
            self._delete_category()

    def _selected_indices(self) -> List[int]:
        return sorted({i.row() for i in self.lst_dorks.selectedIndexes()})

    def _group_or_selected(self) -> None:
        idxs = self._selected_indices()
        if len(idxs) < 2:
            return
        self.vm.make_or_group(idxs)
        cat = self.vm.current_category()
        if cat:
            self._apply_item_styles(cat)

    def _toggle_not_selected(self) -> None:
        idxs = self._selected_indices()
        for i in idxs:
            self.vm.toggle_not(i)
        cat = self.vm.current_category()
        if cat:
            self._apply_item_styles(cat)

    def _save_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "Profili Kaydet", "Profil adı:")
        if not ok or not name.strip():
            return
        self.vm.save_profile(name.strip())

    def _delete_profile(self) -> None:
        name = self.cmb_profiles.currentText().strip()
        if not name:
            return
        if QMessageBox.question(self, "Profili Sil", f"'{name}' profilini silmek istiyor musunuz?") == QMessageBox.Yes:
            self.vm.delete_profile(name)

    # ====== Category CRUD ======
    def _create_category(self) -> None:
        name, ok = QInputDialog.getText(self, "Yeni Kategori", "Ad:")
        if not ok or not name.strip():
            return
        self.vm.create_category(name.strip())

    def _rename_category(self) -> None:
        c = self.vm.current_category()
        if not c:
            return
        name, ok = QInputDialog.getText(self, "Yeniden Adlandır", "Yeni ad:", text=c.label)
        if not ok or not name.strip():
            return
        self.vm.rename_current_category(name.strip())

    def _delete_category(self) -> None:
        c = self.vm.current_category()
        if not c:
            return
        if QMessageBox.question(self, "Sil", f"'{c.label}' kategorisi silinsin mi?") == QMessageBox.Yes:
            self.vm.delete_current_category()

    # ====== Dork CRUD ======
    def _add_dork(self) -> None:
        cat = self.vm.current_category()
        if not cat:
            return
        text, ok = QInputDialog.getText(self, "Dork Ekle", "Dork:")
        if not ok or not text.strip():
            return
        self.vm.add_dork(text.strip())

    def _delete_dork(self) -> None:
        cat = self.vm.current_category()
        if not cat:
            return
        idxs = self._selected_indices()
        if not idxs:
            return
        if QMessageBox.question(self, "Dork Sil", f"Seçili dork(lar) silinsin mi?") == QMessageBox.Yes:
            self.vm.delete_dorks(idxs)
