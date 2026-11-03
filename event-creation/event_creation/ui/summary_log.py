"""Right column result area: placeholder → summary bar + one-column FULL LOG.

Non-modal: consecutive operations append to the log; Undo removes the last
operation's entries; OK clears everything back to the placeholder.
"""
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QPushButton, QStackedWidget,
                               QStyle, QStyledItemDelegate, QToolButton,
                               QVBoxLayout, QWidget)

from . import theme
from .theme import PALETTE

IdRole = Qt.UserRole + 1
MarkerRole = Qt.UserRole + 2

_MARKER_COLORS = {
    "W": PALETTE["green"],
    "F": PALETTE["text_dim"],
    "E": PALETTE["accent_light"],
}
_KIND_TO_MARKER = {"workunit": "W", "folder": "F", "event": "E"}


class _LogDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 20)

    def paint(self, painter, option, index):
        painter.save()
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor(PALETTE["selection_bg"]))
        marker = index.data(MarkerRole) or "E"
        painter.setFont(theme.mono_font(8.5))
        painter.setPen(QColor(_MARKER_COLORS.get(marker, PALETTE["text_dim"])))
        painter.drawText(option.rect.adjusted(8, 0, 0, 0), Qt.AlignVCenter, marker)

        painter.setFont(theme.mono_font(11.5))
        painter.setPen(QColor("#d5dae2"))
        fm = QFontMetrics(painter.font())
        text = fm.elidedText(index.data(Qt.DisplayRole) or "", Qt.ElideRight,
                             option.rect.width() - 34)
        painter.drawText(option.rect.adjusted(26, 0, -4, 0), Qt.AlignVCenter, text)
        painter.restore()


class SummaryLog(QWidget):
    undoRequested = Signal()
    selectRequested = Signal(str)
    cleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._op_sizes = []      # entries added per operation, for Undo removal

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        # -- page 0: placeholder ------------------------------------------
        placeholder = QFrame()
        placeholder.setObjectName("Placeholder")
        pl = QVBoxLayout(placeholder)
        pl.setAlignment(Qt.AlignCenter)
        check = QLabel("✓")
        check.setAlignment(Qt.AlignCenter)
        check.setStyleSheet(
            f"color: {PALETTE['text_disabled']}; font-size: 18px;"
            f"border: 1px solid {PALETTE['text_disabled']}; border-radius: 16px;"
            "min-width: 32px; max-width: 32px; min-height: 32px; max-height: 32px;")
        pl.addWidget(check, 0, Qt.AlignHCenter)
        hint = QLabel("created items will appear here")
        hint.setObjectName("PlaceholderText")
        hint.setAlignment(Qt.AlignCenter)
        pl.addWidget(hint)
        self.stack.addWidget(placeholder)

        # -- page 1: summary + log ----------------------------------------
        results = QWidget()
        rl = QVBoxLayout(results)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)

        bar = QFrame()
        bar.setObjectName("SuccessBar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(12, 10, 12, 10)
        bl.setSpacing(10)
        ok_circle = QLabel("✓")
        ok_circle.setAlignment(Qt.AlignCenter)
        ok_circle.setStyleSheet(
            f"color: {PALETTE['green']}; font-size: 16px; font-weight: 700;"
            f"background: {PALETTE['green_bg']}; border: 1px solid {PALETTE['green_border']};"
            "border-radius: 16px; min-width: 32px; max-width: 32px;"
            "min-height: 32px; max-height: 32px;")
        bl.addWidget(ok_circle)

        mid = QVBoxLayout()
        mid.setSpacing(2)
        self.count_label = QLabel("0 created")
        self.count_label.setObjectName("SuccessCount")
        mid.addWidget(self.count_label)
        self.path_label = QLabel("")
        self.path_label.setObjectName("SuccessPath")
        mid.addWidget(self.path_label)
        bl.addLayout(mid, 1)

        self.undo_btn = QPushButton("↩ Undo")
        self.undo_btn.clicked.connect(self.undoRequested)
        bl.addWidget(self.undo_btn)
        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("OkButton")
        ok_btn.clicked.connect(self.clear)
        bl.addWidget(ok_btn)
        rl.addWidget(bar)

        self.warn_label = QLabel("")
        self.warn_label.setStyleSheet(
            f"color: {PALETTE['warning']}; font-size: 11px;")
        self.warn_label.setWordWrap(True)
        self.warn_label.setVisible(False)
        rl.addWidget(self.warn_label)

        card = QFrame()
        card.setObjectName("LogCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(8, 6, 8, 8)
        cl.setSpacing(4)
        self.log_header = QToolButton()
        self.log_header.setObjectName("LogHeader")
        self.log_header.setText("▾ FULL LOG")
        self.log_header.setCheckable(True)
        self.log_header.setChecked(True)
        self.log_header.toggled.connect(self._toggle_log)
        cl.addWidget(self.log_header, 0, Qt.AlignLeft)

        self.log_list = QListWidget()
        self.log_list.setObjectName("LogList")
        self.log_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.log_list.setItemDelegate(_LogDelegate(self.log_list))
        self.log_list.itemClicked.connect(self._on_item_clicked)
        cl.addWidget(self.log_list, 1)
        rl.addWidget(card, 1)

        self.stack.addWidget(results)
        self.stack.setCurrentIndex(0)

    # -- API ---------------------------------------------------------------

    def add_operation(self, result):
        """Append a successful OperationResult to the log and update the summary."""
        added = 0
        for item in result.created:
            marker = _KIND_TO_MARKER.get(item.kind, "E")
            li = QListWidgetItem(item.name)
            li.setData(IdRole, item.object_id)
            li.setData(MarkerRole, marker)
            self.log_list.addItem(li)
            added += 1
        self._op_sizes.append(added)

        extras = []
        if result.skipped:
            extras.append(f"{len(result.skipped)} skipped (already exist)")
        if result.incorrect_sources:
            extras.append(f"{len(result.incorrect_sources)} sources without "
                          f"an expected keyword")
        self.warn_label.setText(" · ".join(extras))
        self.warn_label.setVisible(bool(extras))

        self._update_counter(result.destination_path)
        self.undo_btn.setEnabled(True)
        self.stack.setCurrentIndex(1)
        self.log_list.scrollToBottom()

    def pop_last_operation(self):
        """Remove the last operation's entries after a successful Undo."""
        if not self._op_sizes:
            return
        for _ in range(self._op_sizes.pop()):
            self.log_list.takeItem(self.log_list.count() - 1)
        self.warn_label.setVisible(False)
        self.undo_btn.setEnabled(False)
        if self.log_list.count() == 0:
            self.clear()
        else:
            self._update_counter("")

    def clear(self):
        self.log_list.clear()
        self._op_sizes.clear()
        self.warn_label.setVisible(False)
        self.stack.setCurrentIndex(0)
        self.cleared.emit()

    # -- internals ---------------------------------------------------------

    def _update_counter(self, dest_path: str):
        self.count_label.setText(f"{self.log_list.count()} created")
        if dest_path:
            fm = QFontMetrics(self.path_label.font())
            self.path_label.setText(fm.elidedText(f"in {dest_path}", Qt.ElideMiddle, 320))

    def _toggle_log(self, expanded: bool):
        self.log_list.setVisible(expanded)
        self.log_header.setText("▾ FULL LOG" if expanded else "▸ FULL LOG")

    def _on_item_clicked(self, item: QListWidgetItem):
        object_id = item.data(IdRole)
        if object_id:
            self.selectRequested.emit(object_id)
