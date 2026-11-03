"""Main window: two-column layout, toolbar, status bar, settings overlay,
and wiring to the WAAPI worker thread."""
import logging
import sys

from PySide6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, Qt,
                            QThread, QTimer, Signal)
from PySide6.QtGui import QFontMetrics, QIcon
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMainWindow, QPushButton,
                               QSplitter, QVBoxLayout, QWidget)

from .. import __version__
from ..paths import resource_dir
from . import theme
from .container_form import ContainerForm
from .settings_panel import SettingsPanel
from .summary_log import SummaryLog
from .target_list import TargetListPanel
from .theme import PALETTE
from .worker import WaapiWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    requestConnect = Signal()
    requestRefresh = Signal()
    requestCreate = Signal(str, object)
    requestUndo = Signal()
    requestSelect = Signal(str)
    requestPing = Signal()
    requestShutdown = Signal()

    def __init__(self, settings_manager):
        super().__init__()
        self.settings = settings_manager
        self._targets = []
        self._selection_count = 0
        self._loop_count = 0
        self._connected = False
        self._busy = False
        self._settings_valid = True
        self._sentence = ("", False)
        self._transient = None
        self._select_after_refresh = None

        self.setWindowTitle("Event Creation")
        icon_path = resource_dir() / "icons" / "warpp_logo_black.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(900, 560)
        self.setMinimumSize(700, 420)

        central = QWidget()
        central.setObjectName("Central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- toolbar ----
        toolbar = QWidget()
        toolbar.setObjectName("Toolbar")
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(12, 8, 12, 8)
        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background: {PALETTE['accent']}; border-radius: 2px;")
        tl.addWidget(dot)
        title = QLabel("Event Creation")
        title.setObjectName("TitleLabel")
        tl.addWidget(title)
        tl.addStretch(1)
        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.setObjectName("SettingsButton")
        self.settings_btn.setCheckable(True)
        self.settings_btn.toggled.connect(self._toggle_settings)
        tl.addWidget(self.settings_btn)
        version = QLabel(f"v{__version__}")
        version.setObjectName("VersionLabel")
        tl.addWidget(version)
        root.addWidget(toolbar)

        # ---- columns ----
        self.splitter = QSplitter(Qt.Horizontal)
        self.targets_panel = TargetListPanel()
        self.targets_panel.setMinimumWidth(260)
        self.splitter.addWidget(self.targets_panel)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(12, 12, 12, 12)
        rl.setSpacing(10)
        self.container_form = ContainerForm()
        self.container_form.setVisible(False)
        rl.addWidget(self.container_form)
        self.summary = SummaryLog()
        rl.addWidget(self.summary, 1)
        self.splitter.addWidget(right)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([300, 560])
        root.addWidget(self.splitter, 1)

        # ---- status bar ----
        status = QWidget()
        status.setObjectName("StatusBar")
        sl = QHBoxLayout(status)
        sl.setContentsMargins(12, 8, 12, 8)
        sl.setSpacing(8)
        self.conn_dot = QLabel()
        self.conn_dot.setFixedSize(6, 6)
        sl.addWidget(self.conn_dot)
        self.project_label = QLabel("Not Connected")
        self.project_label.setObjectName("ProjectLabel")
        sl.addWidget(self.project_label)
        self.sentence_label = QLabel("")
        self.sentence_label.setObjectName("StatusSentence")
        self.sentence_label.setMinimumWidth(60)
        sl.addWidget(self.sentence_label, 1)
        self.create_btn = QPushButton("Create Events")
        self.create_btn.setObjectName("CreateButton")
        self.create_btn.clicked.connect(self._on_create_clicked)
        sl.addWidget(self.create_btn)
        root.addWidget(status)

        # ---- settings overlay ----
        self.dim = QWidget(central)
        self.dim.setStyleSheet("background: rgba(0, 0, 0, 150);")
        self.dim.hide()
        self.dim.mousePressEvent = lambda e: self.settings_btn.setChecked(False)
        self.settings_panel = SettingsPanel(self.settings, central)
        self.settings_panel.hide()
        self.settings_panel.closeRequested.connect(
            lambda: self.settings_btn.setChecked(False))
        self.settings_panel.validityChanged.connect(self._on_settings_validity)
        self.settings_panel.settingsChanged.connect(self._update_state)
        self._panel_anim = QPropertyAnimation(self.settings_panel, b"pos", self)
        self._panel_anim.setDuration(160)
        self._panel_anim.setEasingCurve(QEasingCurve.OutCubic)

        # ---- component wiring ----
        self.targets_panel.selectionChanged.connect(self._on_target_selected)
        self.targets_panel.refreshRequested.connect(self._on_refresh_clicked)
        self.targets_panel.containerRequested.connect(self._open_container_form)
        self.container_form.cancelled.connect(self._close_container_form)
        self.container_form.validityChanged.connect(lambda _: self._update_state())
        self.summary.undoRequested.connect(self._on_undo_clicked)
        self.summary.selectRequested.connect(self.requestSelect)
        self.summary.cleared.connect(self._update_state)

        # ---- worker thread ----
        self.worker = WaapiWorker()
        self.worker.set_settings(self.settings)
        self._thread = QThread(self)
        self.worker.moveToThread(self._thread)
        self.requestConnect.connect(self.worker.connect_and_refresh)
        self.requestRefresh.connect(self.worker.refresh)
        self.requestCreate.connect(self.worker.create)
        self.requestUndo.connect(self.worker.undo)
        self.requestSelect.connect(self.worker.select_object)
        self.requestPing.connect(self.worker.ping)
        self.requestShutdown.connect(self.worker.shutdown)
        self.worker.connectionChanged.connect(self._on_connection_changed)
        self.worker.targetsLoaded.connect(self._on_targets_loaded)
        self.worker.selectionCountChanged.connect(self._on_selection_count)
        self.worker.operationFinished.connect(self._on_operation_finished)
        self.worker.undoFinished.connect(self._on_undo_finished)
        self.worker.error.connect(self._show_transient)
        self._thread.start()

        self._ping_timer = QTimer(self)
        self._ping_timer.setInterval(4000)
        self._ping_timer.timeout.connect(self.requestPing)
        self._ping_timer.start()

        self._update_state()
        QTimer.singleShot(0, self.requestConnect.emit)

    # ------------------------------------------------------------------ state

    def _update_state(self):
        item = self.targets_panel.current_item()
        form_open = self.container_form.isVisible()
        form_ok = self.container_form.valid if form_open else True
        # One operation at a time: the log must match what Undo would revert
        result_open = self.summary.log_list.count() > 0

        self.conn_dot.setStyleSheet(
            f"background: {PALETTE['green'] if self._connected else PALETTE['error']};"
            "border-radius: 3px;")

        warning = False
        if self._transient:
            sentence, warning = self._transient, True
        elif not self._connected:
            sentence, warning = "start Wwise and press ⟳ to connect", True
        elif result_open:
            sentence, warning = "! press OK or Undo to create more events", True
        elif not item:
            sentence, warning = "! select a destination in the list", True
        elif not self._settings_valid:
            sentence, warning = "! fix the highlighted fields in Settings", True
        elif form_open and not form_ok:
            sentence, warning = "! fix the container name", True
        else:
            # A loop produces an extra Stop event when the option is enabled.
            n = self._selection_count
            if self.settings.get('STOP_EVENT_FOR_LOOPS', False):
                n += self._loop_count
            events_part = f"{n} event{'s' if n != 1 else ''}"
            if form_open:
                kind = "work unit" if self.container_form.kind == "WorkUnit" else "folder"
                dest = f"{item['path']}\\{self.container_form.name()}"
                sentence = f"{events_part} + 1 {kind} → {dest}"
            else:
                sentence = f"{events_part} → {item['path']}"
            if self._selection_count == 0:
                sentence = "no playable objects selected in Wwise"
                warning = True

        self._sentence = (sentence, warning)
        self._apply_sentence()

        self.targets_panel.set_plus_enabled(bool(item) and self._connected
                                            and not form_open)
        can_create = (self._connected and item is not None and not self._busy
                      and self._settings_valid and form_ok and not result_open)
        self.create_btn.setEnabled(can_create)

        if form_open and item:
            label = ("parent of new work unit" if self.container_form.kind == "WorkUnit"
                     else "parent of new folder")
            self.targets_panel.set_pending(item["id"], label)
        else:
            self.targets_panel.set_pending(None)

    def _apply_sentence(self):
        text, warning = self._sentence
        fm = QFontMetrics(self.sentence_label.font())
        self.sentence_label.setText(
            fm.elidedText(text, Qt.ElideMiddle, max(60, self.sentence_label.width() - 8)))
        self.sentence_label.setProperty("warning", warning)
        self.sentence_label.style().unpolish(self.sentence_label)
        self.sentence_label.style().polish(self.sentence_label)

    def _show_transient(self, message):
        self._transient = message
        self._update_state()
        QTimer.singleShot(6000, self._clear_transient)

    def _clear_transient(self):
        self._transient = None
        self._update_state()

    # ------------------------------------------------------------- worker slots

    def _on_connection_changed(self, connected, project_name):
        self._connected = connected
        self.project_label.setText(project_name)
        if not connected and self.summary.log_list.count():
            # Wwise's undo history may not survive a lost connection (e.g. a restart)
            self.summary.clear()
            self._show_transient("Lost connection to Wwise")
        self._update_state()

    def _on_targets_loaded(self, targets):
        self._targets = targets
        self.targets_panel.set_targets(targets)
        self.container_form.update_targets(targets)
        if self._select_after_refresh:
            row = self.targets_panel.model.row_for_id(self._select_after_refresh)
            if row >= 0:
                proxy_index = self.targets_panel.proxy.mapFromSource(
                    self.targets_panel.model.index(row, 0))
                if proxy_index.isValid():
                    self.targets_panel.view.setCurrentIndex(proxy_index)
            self._select_after_refresh = None
        self._update_state()

    def _on_selection_count(self, playable, loops):
        self._selection_count = playable
        self._loop_count = loops
        self._update_state()

    def _on_operation_finished(self, result):
        self._busy = False
        if result.ok:
            self.summary.add_operation(result)
            if self.container_form.isVisible():
                created_container = next(
                    (c for c in result.created if c.kind in ("workunit", "folder")), None)
                if created_container:
                    self._select_after_refresh = created_container.object_id
                self._close_container_form()
        else:
            self._show_transient(f"✕ {result.error}")
        self._update_state()

    def _on_undo_finished(self, ok, message):
        if ok:
            self.summary.pop_last_operation()
        else:
            self._show_transient(message)
        self._update_state()

    # ---------------------------------------------------------------- actions

    def _on_refresh_clicked(self):
        self.requestRefresh.emit()

    def _on_create_clicked(self):
        item = self.targets_panel.current_item()
        if not item:
            return
        container = None
        if self.container_form.isVisible():
            if not self.container_form.valid:
                return
            container = (self.container_form.kind, self.container_form.name())
        self._busy = True
        self._update_state()
        self.requestCreate.emit(item["path"], container)

    def _on_undo_clicked(self):
        self.requestUndo.emit()

    def _on_target_selected(self, item):
        if self.container_form.isVisible():
            if item is None:
                self._close_container_form()
            else:
                self.container_form.parent_item = item
                self.container_form._validate()
        self._update_state()

    def _open_container_form(self, kind):
        item = self.targets_panel.current_item()
        if not item:
            return
        self.container_form.open_for(kind, item, self._targets, theme.FONT_MONO)
        self.container_form.setVisible(True)
        self._update_state()

    def _close_container_form(self):
        self.container_form.setVisible(False)
        self._update_state()

    # ------------------------------------------------------------ settings panel

    def _toggle_settings(self, open_):
        central = self.centralWidget()
        if open_:
            self.dim.setGeometry(central.rect())
            self.dim.show()
            self.dim.raise_()
            self.settings_panel.move(central.width(), 0)
            self.settings_panel.setFixedHeight(central.height())
            self.settings_panel.show()
            self.settings_panel.raise_()
            self._panel_anim.stop()
            self._panel_anim.setStartValue(self.settings_panel.pos())
            self._panel_anim.setEndValue(
                QPoint(central.width() - self.settings_panel.WIDTH, 0))
            self._panel_anim.start()
            self.settings_panel.setFocus()
        else:
            self.dim.hide()
            self.settings_panel.hide()

    def _on_settings_validity(self, valid):
        self._settings_valid = valid
        self._update_state()

    # ---------------------------------------------------------------- events

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.settings_btn.isChecked():
                self.settings_btn.setChecked(False)
                return
            if self.container_form.isVisible():
                self._close_container_form()
                return
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        central = self.centralWidget()
        if self.dim.isVisible():
            self.dim.setGeometry(central.rect())
        if self.settings_panel.isVisible():
            self.settings_panel.setFixedHeight(central.height())
            self.settings_panel.move(central.width() - self.settings_panel.WIDTH, 0)
        self._apply_sentence()

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            self._enable_dark_titlebar()

    def _enable_dark_titlebar(self):
        try:
            import ctypes
            hwnd = int(self.winId())
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            pass

    def closeEvent(self, event):
        self._ping_timer.stop()
        self._thread.quit()
        self._thread.wait(3000)
        # The thread's event loop is stopped, so it is safe to close the
        # WAAPI connection directly from here.
        self.worker.shutdown()
        super().closeEvent(event)
