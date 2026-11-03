"""Left column: filterable flat list of destination Work Units / Folders."""
from PySide6.QtCore import (QAbstractListModel, QItemSelectionModel,
                            QModelIndex, QSize, QSortFilterProxyModel, Qt,
                            Signal)
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QListView, QMenu,
                               QStyle, QStyledItemDelegate, QToolButton,
                               QVBoxLayout, QWidget)

from ..core.project import get_parent_path
from ..paths import resource_dir
from . import theme
from .theme import PALETTE

IdRole = Qt.UserRole + 1
NameRole = Qt.UserRole + 2
PathRole = Qt.UserRole + 3
TypeRole = Qt.UserRole + 4
ParentPathRole = Qt.UserRole + 5


class TargetModel(QAbstractListModel):
    def __init__(self):
        super().__init__()
        self._items = []

    def set_items(self, items: list):
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        item = self._items[index.row()]
        if role in (Qt.DisplayRole, NameRole):
            return item["name"]
        if role == IdRole:
            return item["id"]
        if role == PathRole:
            return item["path"]
        if role == ParentPathRole:
            return get_parent_path(item["path"]) or "\\"
        if role == TypeRole:
            return item["type"]
        return None

    def row_for_id(self, object_id: str) -> int:
        for i, item in enumerate(self._items):
            if item["id"] == object_id:
                return i
        return -1


class TargetFilterProxy(QSortFilterProxyModel):
    """Token search: every space-separated token must be a substring of the
    name or the path (case-insensitive). Rows are ranked: match in the name
    beats a word-boundary match beats a path-only match."""

    def __init__(self):
        super().__init__()
        self._tokens = []
        self.setDynamicSortFilter(True)

    def set_query(self, text: str):
        self._tokens = [t for t in text.lower().split() if t]
        self.invalidate()
        self.sort(0)

    def _score(self, index) -> int:
        if not self._tokens:
            return 0
        name = (index.data(NameRole) or "").lower()
        path = (index.data(PathRole) or "").lower()
        score = 0
        for tok in self._tokens:
            if tok in name:
                if name.startswith(tok) or f"_{tok}" in name or f" {tok}" in name:
                    score += 3
                else:
                    score += 2
            elif tok in path:
                score += 1
            else:
                return -1
        return score

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._tokens:
            return True
        index = self.sourceModel().index(source_row, 0, source_parent)
        return self._score(index) >= 0

    def lessThan(self, left, right):
        ls, rs = self._score(left), self._score(right)
        if ls != rs:
            return ls > rs
        return left.row() < right.row()


class TargetDelegate(QStyledItemDelegate):
    """Two-line row: name + parent path, type swatch, selection/pending bars."""

    def __init__(self, view):
        super().__init__(view)
        self.pending_parent_id = None
        self.pending_kind_label = ""   # e.g. "parent of new work unit"

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 42)

    def paint(self, painter: QPainter, option, index):
        painter.save()
        rect = option.rect
        selected = bool(option.state & QStyle.State_Selected)
        is_pending = (self.pending_parent_id
                      and index.data(IdRole) == self.pending_parent_id)

        if selected:
            painter.fillRect(rect, QColor(PALETTE["selection_bg"]))
            painter.fillRect(rect.x(), rect.y(), 2, rect.height(),
                             QColor(PALETTE["accent_light"]))
        if is_pending:
            painter.fillRect(rect.x(), rect.y(), 2, rect.height(),
                             QColor(PALETTE["green"]))

        obj_type = index.data(TypeRole)
        swatch = QColor(PALETTE["swatch_wwu"] if obj_type == "WorkUnit"
                        else PALETTE["swatch_folder"])
        if is_pending:
            swatch = QColor(PALETTE["green"])
        painter.fillRect(rect.x() + 10, rect.y() + 9, 12, 10, swatch)

        text_x = rect.x() + 30
        text_w = rect.width() - 38

        name_font = theme.mono_font(12.5)
        painter.setFont(name_font)
        painter.setPen(QColor(PALETTE["text_strong"] if selected else PALETTE["text"]))
        fm = painter.fontMetrics()
        name = fm.elidedText(index.data(NameRole) or "", Qt.ElideRight, text_w)
        painter.drawText(text_x, rect.y() + 6 + fm.ascent(), name)

        path_font = theme.mono_font(9.5)
        painter.setFont(path_font)
        if is_pending and self.pending_kind_label:
            painter.setPen(QColor(PALETTE["green_text"]))
            second = self.pending_kind_label
        else:
            painter.setPen(QColor("#7c8593" if selected else PALETTE["text_faint"]))
            second = index.data(ParentPathRole) or ""
        fm2 = painter.fontMetrics()
        painter.drawText(text_x, rect.y() + 24 + fm2.ascent(),
                         fm2.elidedText(second, Qt.ElideRight, text_w))
        painter.restore()


def _swatch_icon(color: str) -> QIcon:
    pm = QPixmap(12, 12)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.fillRect(1, 2, 10, 8, QColor(color))
    p.end()
    return QIcon(pm)


class TargetListPanel(QWidget):
    selectionChanged = Signal(object)          # dict {id,name,path,type} or None
    refreshRequested = Signal()
    containerRequested = Signal(str)           # "WorkUnit" | "Folder"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LeftColumn")
        self._restoring = False
        self.model = TargetModel()
        self.proxy = TargetFilterProxy()
        self.proxy.setSourceModel(self.model)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter…")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        top.addWidget(self.filter_edit, 1)

        self.refresh_btn = QToolButton()
        self.refresh_btn.setObjectName("RefreshButton")
        icon_path = resource_dir() / "icons" / "refresh_icon.png"
        if icon_path.exists():
            self.refresh_btn.setIcon(QIcon(str(icon_path)))
        else:
            self.refresh_btn.setText("⟳")
        self.refresh_btn.clicked.connect(self.refreshRequested)
        top.addWidget(self.refresh_btn)
        layout.addLayout(top)

        self.view = QListView()
        self.view.setObjectName("TargetList")
        self.view.setModel(self.proxy)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setUniformItemSizes(True)
        self.view.setSelectionMode(QListView.SingleSelection)
        self.delegate = TargetDelegate(self.view)
        self.view.setItemDelegate(self.delegate)
        self.view.selectionModel().selectionChanged.connect(self._on_selection)
        layout.addWidget(self.view, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.plus_btn = QToolButton()
        self.plus_btn.setObjectName("PlusButton")
        self.plus_btn.setText("＋")
        self.plus_btn.setPopupMode(QToolButton.InstantPopup)
        self.plus_btn.setEnabled(False)
        self._menu = QMenu(self.plus_btn)
        self._menu.aboutToShow.connect(self._build_menu)
        self.plus_btn.setMenu(self._menu)
        footer.addWidget(self.plus_btn)

        self.footer_caption = QLabel("select a destination first")
        self.footer_caption.setObjectName("MutedCaption")
        footer.addWidget(self.footer_caption, 1)
        layout.addLayout(footer)

    # -- data --------------------------------------------------------------

    def set_targets(self, items: list):
        """Replace list contents, keeping filter text, selection (by GUID) and scroll."""
        selected = self.current_item()
        selected_id = selected["id"] if selected else None
        scroll = self.view.verticalScrollBar().value()

        # Suppress intermediate selection-cleared notifications while the list
        # is rebuilt, so an open container form doesn't get closed by a refresh.
        self._restoring = True
        self.model.set_items(items)
        self.proxy.set_query(self.filter_edit.text())

        if selected_id is not None:
            row = self.model.row_for_id(selected_id)
            if row >= 0:
                proxy_index = self.proxy.mapFromSource(self.model.index(row, 0))
                if proxy_index.isValid():
                    self.view.selectionModel().select(
                        proxy_index, QItemSelectionModel.ClearAndSelect)
                    self.view.setCurrentIndex(proxy_index)
        self.view.verticalScrollBar().setValue(scroll)
        self._restoring = False
        self._on_selection()

    def current_item(self):
        indexes = self.view.selectionModel().selectedIndexes() if self.view.selectionModel() else []
        if not indexes:
            return None
        idx = indexes[0]
        return {
            "id": idx.data(IdRole),
            "name": idx.data(NameRole),
            "path": idx.data(PathRole),
            "type": idx.data(TypeRole),
        }

    def set_pending(self, parent_id: str | None, kind_label: str = ""):
        self.delegate.pending_parent_id = parent_id
        self.delegate.pending_kind_label = kind_label
        self.view.viewport().update()

    def set_plus_enabled(self, enabled: bool):
        self.plus_btn.setEnabled(enabled)
        self.footer_caption.setText(
            "create new work unit or folder" if enabled else "select a destination first")

    # -- internals ---------------------------------------------------------

    def _on_filter_changed(self, text):
        self.proxy.set_query(text)

    def _on_selection(self, *_):
        if self._restoring:
            return
        self.selectionChanged.emit(self.current_item())

    def _build_menu(self):
        self._menu.clear()
        item = self.current_item()
        parent_name = (item["name"] if item else "").upper()
        header = self._menu.addAction(f"CREATE IN {parent_name}")
        header.setEnabled(False)
        wwu = self._menu.addAction(_swatch_icon(PALETTE["green"]), "Work unit")
        wwu.triggered.connect(lambda: self.containerRequested.emit("WorkUnit"))
        folder = self._menu.addAction(_swatch_icon("#7c8593"), "Folder")
        folder.triggered.connect(lambda: self.containerRequested.emit("Folder"))
        self._menu.setMinimumWidth(196)
