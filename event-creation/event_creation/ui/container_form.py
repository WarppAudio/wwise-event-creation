"""Right-column card: pending new Work Unit / Folder.

Nothing is created in Wwise here — the container is created together with the
events on Create Events (single undo group). This form only holds the pending
name and validates it live against the cached target list.
"""
import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QToolButton, QVBoxLayout, QWidget)

from ..core.naming import is_valid_object_name
from ..core.project import can_create_folder, can_create_workunit
from .theme import PALETTE


class ContainerForm(QFrame):
    cancelled = Signal()
    validityChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ContainerForm")
        self.kind = "WorkUnit"
        self.parent_item = None
        self.targets = []
        self.valid = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QFrame()
        header.setObjectName("ContainerFormHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 8, 8, 8)
        self.swatch = QLabel()
        self.swatch.setFixedSize(12, 10)
        self.swatch.setStyleSheet(f"background: {PALETTE['green']}; border: none;")
        hl.addWidget(self.swatch)
        self.title = QLabel("New work unit")
        self.title.setObjectName("ContainerFormTitle")
        hl.addWidget(self.title, 1)
        close = QToolButton()
        close.setObjectName("CloseButton")
        close.setText("✕")
        close.clicked.connect(self.cancelled)
        hl.addWidget(close)
        outer.addWidget(header)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(12, 10, 12, 12)
        bl.setSpacing(6)

        name_label = QLabel("Name")
        name_label.setObjectName("FieldLabel")
        bl.addWidget(name_label)

        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("ContainerNameEdit")
        self.name_edit.textChanged.connect(self._validate)
        self.name_edit.returnPressed.connect(self.name_edit.clearFocus)
        bl.addWidget(self.name_edit)

        self.error_label = QLabel("")
        self.error_label.setObjectName("FormError")
        self.error_label.setVisible(False)
        bl.addWidget(self.error_label)

        dest_label = QLabel("Will be created in")
        dest_label.setObjectName("FieldLabel")
        bl.addWidget(dest_label)

        self.path_label = QLabel("")
        self.path_label.setWordWrap(True)
        self.path_label.setTextFormat(Qt.RichText)
        self.path_label.setStyleSheet(
            f"color: {PALETTE['text']}; font-family: monospace; font-size: 11px;")
        bl.addWidget(self.path_label)

        note = QLabel("created together with the events on Create Events")
        note.setObjectName("MutedCaption")
        bl.addWidget(note)
        outer.addWidget(body)

    # -- API ---------------------------------------------------------------

    def open_for(self, kind: str, parent_item: dict, targets: list, mono_family: str):
        self.kind = kind
        self.parent_item = parent_item
        self.targets = targets
        self._mono = mono_family
        is_wwu = kind == "WorkUnit"
        self.title.setText("New work unit" if is_wwu else "New folder")
        self.swatch.setStyleSheet(
            f"background: {PALETTE['green'] if is_wwu else '#7c8593'}; border: none;")
        default = f"New_{'Work_Unit' if is_wwu else 'Folder'}"
        self.name_edit.setText(default)
        self.name_edit.setFocus()
        self.name_edit.selectAll()
        self._validate()

    def name(self) -> str:
        return self.name_edit.text().strip()

    def update_targets(self, targets: list):
        self.targets = targets
        if self.isVisible():
            self._validate()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
            return
        super().keyPressEvent(event)

    # -- internals ---------------------------------------------------------

    def _validate(self):
        name = self.name()
        parent_path = self.parent_item["path"] if self.parent_item else ""
        error = ""
        if not name:
            error = "Name cannot be empty"
        elif not is_valid_object_name(name):
            error = 'Name contains an invalid character (\\ / : * ? " < > |)'
        elif self.kind == "WorkUnit" and not can_create_workunit(name, parent_path, self.targets):
            error = "A work unit or folder with this name already exists"
        elif self.kind == "Folder" and not can_create_folder(name, parent_path, self.targets):
            error = "An object with this name already exists in this location"

        self.valid = not error
        self.error_label.setText(error)
        self.error_label.setVisible(bool(error))
        self.name_edit.setProperty("invalid", bool(error))
        self.name_edit.style().unpolish(self.name_edit)
        self.name_edit.style().polish(self.name_edit)

        mono = getattr(self, "_mono", "Consolas")
        path_html = html.escape(parent_path).replace("\\", "\\<wbr>")
        name_html = html.escape(name) if name else "…"
        self.path_label.setText(
            f'<span style="font-family:\'{mono}\';">{path_html}\\'
            f'<span style="color:{PALETTE["green_text"]};">{name_html}</span></span>')
        self.validityChanged.emit(self.valid)
