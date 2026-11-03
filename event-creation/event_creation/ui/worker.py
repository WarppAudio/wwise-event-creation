"""All WAAPI traffic runs on a worker QThread so the GUI never freezes."""
import logging

from PySide6.QtCore import QObject, Signal, Slot

from ..core import events, project
from ..core.naming import clean_object_name
from ..core.waapi import WaapiConnection

logger = logging.getLogger(__name__)


class WaapiWorker(QObject):
    """Lives on a QThread; the main window talks to it exclusively via signals."""

    connectionChanged = Signal(bool, str)      # connected, project name
    targetsLoaded = Signal(list)               # [{id, name, path, type}]
    selectionCountChanged = Signal(int, int)   # playable objects, loops among them
    operationFinished = Signal(object)         # OperationResult
    undoFinished = Signal(bool, str)           # ok, message
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self.conn = WaapiConnection()
        self._was_connected = False
        self._undo_container_id = ""   # container created by the last operation

    # -- internals ---------------------------------------------------------

    def _ensure_connected(self) -> bool:
        if self.conn.is_connected():
            return True
        try:
            self.conn.set_url(self._settings.get("WAAPI_URL") or None)
            self.conn.connect()
            self._subscribe_selection()
            self._emit_connected()
            return True
        except Exception:
            logger.info("Wwise not reachable")
            self._emit_disconnected()
            return False

    def _emit_connected(self):
        try:
            name = project.get_project_name(self.conn)
        except Exception:
            name = "Connected"
        self._was_connected = True
        self.connectionChanged.emit(True, name)

    def _emit_disconnected(self):
        self._was_connected = False
        self._undo_container_id = ""
        self.connectionChanged.emit(False, "Not Connected")

    def _selection_counts(self, objs) -> tuple:
        """(playable objects, loops among them) — loop detection identical to
        the one used at creation time, so the preview count matches reality."""
        playable = [o for o in objs if o.get("isPlayable")]
        words_remove = self._settings.get("WORDS_REMOVE", [])
        tokens = self._settings.get("SOUND_NAMING_FOR_LOOPS", [])
        suffix = self._settings.get("NAMING_FOR_LOOPS", "")
        loops = 0
        for o in playable:
            _, is_loop = clean_object_name(o.get("name", ""), words_remove, tokens, suffix)
            loops += int(is_loop)
        return len(playable), loops

    def _subscribe_selection(self):
        def on_selection(**kwargs):
            playable, loops = self._selection_counts(kwargs.get("objects", []))
            # Cross-thread signal emission is queued by Qt — safe from the waapi thread.
            self.selectionCountChanged.emit(playable, loops)
        try:
            self.conn.subscribe("ak.wwise.ui.selectionChanged", on_selection,
                                {"return": ["id", "name", "isPlayable"]})
        except Exception:
            logger.warning("selectionChanged subscription unavailable", exc_info=True)
        self._push_selection_count()

    def _push_selection_count(self):
        try:
            objs = project.get_selected_objects(self.conn)
            self.selectionCountChanged.emit(*self._selection_counts(objs))
        except Exception:
            pass

    # -- slots (invoked via queued connections from the GUI thread) --------

    @Slot()
    def connect_and_refresh(self):
        if self._ensure_connected():
            self.refresh()

    @Slot()
    def refresh(self):
        if not self._ensure_connected():
            return
        try:
            self.targetsLoaded.emit(project.get_targets(self.conn))
            self._push_selection_count()
        except Exception as e:
            logger.exception("Refresh failed")
            self._emit_disconnected()
            self.error.emit(f"Failed to load work units: {e}")

    @Slot(str, object)
    def create(self, target_path, container):
        if not self._ensure_connected():
            self.error.emit("Not connected to Wwise")
            return
        try:
            result = events.create_events(self.conn, self._settings, target_path, container)
            if result.ok:
                self._undo_container_id = next(
                    (c.object_id for c in result.created if c.kind in ("workunit", "folder")), "")
            self.operationFinished.emit(result)
        except Exception as e:
            logger.exception("Create events failed")
            res = events.OperationResult(error=str(e))
            self.operationFinished.emit(res)
        # Refresh targets afterwards (a new container may have appeared)
        try:
            self.targetsLoaded.emit(project.get_targets(self.conn))
        except Exception:
            self._emit_disconnected()

    @Slot()
    def undo(self):
        if not self._ensure_connected():
            self.undoFinished.emit(False, "Not connected to Wwise")
            return
        ok, msg = events.undo_last(self.conn, self._undo_container_id)
        if ok:
            self._undo_container_id = ""
        self.undoFinished.emit(ok, msg)
        try:
            self.targetsLoaded.emit(project.get_targets(self.conn))
        except Exception:
            self._emit_disconnected()

    @Slot(str)
    def select_object(self, object_id):
        if not object_id or not self.conn.is_connected():
            return
        try:
            project.select_in_wwise(self.conn, object_id)
        except Exception:
            logger.exception("Select in Wwise failed")

    @Slot()
    def ping(self):
        """Periodic connection health check driven by a GUI-side timer."""
        if self.conn.is_connected():
            if not self._was_connected:
                self._emit_connected()
        else:
            if self._was_connected:
                self._emit_disconnected()

    @Slot()
    def shutdown(self):
        self.conn.disconnect()

    # settings manager is injected once from the GUI thread before the thread starts
    def set_settings(self, settings_manager):
        self._settings = settings_manager
