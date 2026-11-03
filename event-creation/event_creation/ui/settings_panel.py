"""Slide-in settings panel.

Every field maps to one key in settings.json and is written the moment it
changes, so there is no Save button. Invalid input marks the field and
disables Create Events until it is fixed.
"""
import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QLineEdit, QScrollArea, QToolButton,
                               QVBoxLayout, QWidget)

from ..core.naming import ALLOWED_PATTERN

# WebSocket address of the Wwise Authoring API server.
URL_PATTERN = re.compile(r'^wss?://\S+$')


def _csv_to_list(text: str) -> list:
    return [w.strip() for w in re.split(r',\s*', text) if w.strip()]


class SettingsPanel(QFrame):
    WIDTH = 392

    closeRequested = Signal()
    validityChanged = Signal(bool)
    settingsChanged = Signal()     # any value saved — lets the window refresh previews

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsPanel")
        self.setFixedWidth(self.WIDTH)
        self.settings = settings_manager
        self._invalid = set()
        self._edits = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("Settings")
        title.setObjectName("SettingsTitle")
        head.addWidget(title, 1)
        close = QToolButton()
        close.setObjectName("CloseButton")
        close.setText("✕")
        close.clicked.connect(self.closeRequested)
        head.addWidget(close)
        outer.addLayout(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 6, 0)
        body.setSpacing(10)

        # ---------------- NAMING ----------------
        body.addWidget(self._group_header("NAMING"))

        checks = QHBoxLayout()
        self.capitalize_cb = QCheckBox("Capitalize Events")
        self.lowercase_cb = QCheckBox("Lowercase Events")
        case = self.settings.get('LETTER_CASE_EVENT_NAME', None)
        self.capitalize_cb.setChecked(case == 'upper')
        self.lowercase_cb.setChecked(case == 'lower')
        self.capitalize_cb.toggled.connect(self._on_capitalize)
        self.lowercase_cb.toggled.connect(self._on_lowercase)
        checks.addWidget(self.capitalize_cb)
        checks.addWidget(self.lowercase_cb)
        body.addLayout(checks)

        self.inherit_cb = QCheckBox("Inherit name from parent")
        self.inherit_cb.setChecked(bool(self.settings.get('INHERIT_NAME_FROM_PARENT', False)))
        self.inherit_cb.toggled.connect(
            lambda v: self._set('INHERIT_NAME_FROM_PARENT', bool(v)))
        body.addWidget(self.inherit_cb)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        self._add_text_field(grid, 0, 0, "Play Events Prefix", 'PLAY_NAMING_CONVENTION',
                             kind="prefix")
        self._add_text_field(grid, 0, 1, "Stop Events Prefix", 'STOP_NAMING_CONVENTION',
                             kind="prefix")
        self._add_text_field(grid, 2, 0, "Loop event suffix", 'NAMING_FOR_LOOPS',
                             kind="prefix", placeholder="e.g. Lp")
        self._add_text_field(grid, 2, 1, "Expected source keywords", 'NAMING_CONVENTION',
                             kind="csv", placeholder="e.g. SFX, AMB, VO")
        self._add_text_field(grid, 4, 0, "Loop keywords", 'SOUND_NAMING_FOR_LOOPS',
                             kind="csv", placeholder="e.g. Loop, LP")
        self._add_text_field(grid, 4, 1, "Text to remove", 'WORDS_REMOVE',
                             kind="csv", placeholder="e.g. sfx, temp")
        body.addLayout(grid)

        wide = QGridLayout()
        self._add_text_field(wide, 0, 0, "Case change ignore list",
                             'WORDS_NOT_CAPITALIZE', kind="csv",
                             placeholder="e.g. AMB, UI, SFX#")
        body.addLayout(wide)

        # ---------------- LOOPS ----------------
        body.addWidget(self._group_header("LOOPS"))

        loop_checks = QHBoxLayout()
        self.stop_loops_cb = QCheckBox("Stop Events Loops")
        self.stop_loops_cb.setChecked(bool(self.settings.get('STOP_EVENT_FOR_LOOPS', False)))
        self.stop_loops_cb.toggled.connect(
            lambda v: self._set('STOP_EVENT_FOR_LOOPS', bool(v)))
        self.seek_loops_cb = QCheckBox("Seek Action Loops")
        self.seek_loops_cb.setChecked(bool(self.settings.get('SEEK_ACTION_FOR_LOOPS', False)))
        self.seek_loops_cb.toggled.connect(
            lambda v: self._set('SEEK_ACTION_FOR_LOOPS', bool(v)))
        loop_checks.addWidget(self.stop_loops_cb)
        loop_checks.addWidget(self.seek_loops_cb)
        body.addLayout(loop_checks)

        nums = QGridLayout()
        nums.setHorizontalSpacing(8)
        self._add_number_field(nums, 0, "Play fade loop [s]", 'PLAY_LOOP_FADE_TIME', 0, 60)
        self._add_number_field(nums, 1, "Stop fade loop [s]", 'STOP_LOOP_FADE_TIME', 0, 60)
        self._add_number_field(nums, 2, "Seek %", 'SEEK_Percent', 0, 100)
        self._add_number_field(nums, 3, "Min %", 'SEEK_RANDOM_MIN', -100, 0)
        self._add_number_field(nums, 4, "Max %", 'SEEK_RANDOM_MAX', 0, 100)
        body.addLayout(nums)

        # ---------------- CONNECTION ----------------
        body.addWidget(self._group_header("CONNECTION"))

        conn_grid = QGridLayout()
        self._add_text_field(
            conn_grid, 0, 0, "Wwise WAAPI URL", 'WAAPI_URL', kind="url",
            placeholder="ws://127.0.0.1:8080/waapi")
        body.addLayout(conn_grid)

        body.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

    # -- helpers -----------------------------------------------------------

    def _group_header(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("GroupHeader")
        return lbl

    def _add_text_field(self, grid, row, col, label, key, kind, placeholder: str = ""):
        lbl = QLabel(label)
        lbl.setObjectName("FieldLabel")
        grid.addWidget(lbl, row, col)
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        value = self.settings.get(key)
        edit.setText(', '.join(value) if isinstance(value, list) else (value or ""))
        edit.textChanged.connect(lambda text, k=key, e=edit, kd=kind:
                                 self._on_text_changed(k, e, text, kd))
        grid.addWidget(edit, row + 1, col)
        self._edits[key] = edit

    def _add_number_field(self, grid, col, label, key, lo, hi):
        lbl = QLabel(label)
        lbl.setObjectName("FieldLabel")
        grid.addWidget(lbl, 0, col)
        edit = QLineEdit()
        edit.setText(str(self.settings.get(key, 0.0)))
        edit.textChanged.connect(lambda text, k=key, e=edit, a=lo, b=hi:
                                 self._on_number_changed(k, e, text, a, b))
        grid.addWidget(edit, 1, col)
        self._edits[key] = edit

    def _set(self, key, value):
        self.settings.set(key, value)
        self.settingsChanged.emit()

    def _mark(self, key, edit, ok):
        if ok:
            self._invalid.discard(key)
        else:
            self._invalid.add(key)
        edit.setProperty("invalid", not ok)
        edit.style().unpolish(edit)
        edit.style().polish(edit)
        self.validityChanged.emit(self.is_valid())

    def is_valid(self) -> bool:
        return not self._invalid

    # -- change handlers ---------------------------------------------------

    def _on_text_changed(self, key, edit, text, kind):
        text = text.strip()
        if kind == "prefix":
            if text and not ALLOWED_PATTERN.match(text):
                self._mark(key, edit, False)
                return
            self._set(key, text)
        elif kind == "url":
            if text and not URL_PATTERN.match(text):
                self._mark(key, edit, False)
                return
            self._set(key, text)
        else:  # csv list
            self._set(key, _csv_to_list(text))
        self._mark(key, edit, True)

    def _on_number_changed(self, key, edit, text, lo, hi):
        try:
            value = float(text)
            if not (lo <= value <= hi):
                raise ValueError
        except ValueError:
            self._mark(key, edit, False)
            return
        self._set(key, value)
        self._mark(key, edit, True)

    def _on_capitalize(self, checked):
        if checked:
            self.lowercase_cb.setChecked(False)
        self._save_case()

    def _on_lowercase(self, checked):
        if checked:
            self.capitalize_cb.setChecked(False)
        self._save_case()

    def _save_case(self):
        if self.capitalize_cb.isChecked():
            case = 'upper'
        elif self.lowercase_cb.isChecked():
            case = 'lower'
        else:
            case = None
        self._set('LETTER_CASE_EVENT_NAME', case)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.closeRequested.emit()
            return
        super().keyPressEvent(event)
