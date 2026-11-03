"""The Create Events operation: payload building + a single undoable WAAPI transaction."""
import logging
from dataclasses import dataclass, field

from .naming import format_event_name, clean_object_name
from .project import (get_all_event_names, get_children, get_incorrect_sources,
                      get_selected_objects)

logger = logging.getLogger(__name__)


@dataclass
class CreatedItem:
    kind: str          # "workunit" | "folder" | "event"
    name: str
    object_id: str = ""


@dataclass
class OperationResult:
    created: list = field(default_factory=list)      # [CreatedItem]
    skipped: list = field(default_factory=list)      # event names that already existed
    incorrect_sources: list = field(default_factory=list)
    destination_path: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error


def _build_play(event_name, target, is_loop, settings):
    action = {"type": "Action", "@ActionType": 1, "name": "Start", "@Target": target}
    if is_loop:
        action["@FadeTime"] = settings.get("PLAY_LOOP_FADE_TIME", 0.0)
    return {"type": "Event", "name": event_name, "children": [action]}


def _build_stop(event_name, target, settings):
    action = {"type": "Action", "@ActionType": 2, "name": "",
              "@FadeTime": settings.get("STOP_LOOP_FADE_TIME", 0.0), "@Target": target}
    return {"type": "Event", "name": event_name, "children": [action]}


def _build_seek(event_name, target, settings):
    return {"type": "Event", "name": event_name, "children": [
        {"type": "Action", "@ActionType": 1,
         "@FadeTime": settings.get("PLAY_LOOP_FADE_TIME", 0.0),
         "name": "Start", "@Target": target},
        {"type": "Action", "@ActionType": 36,
         "@SeekPercent": settings.get("SEEK_Percent", 0.0),
         "@Inclusion": True, "name": "Seek", "@Target": target},
    ]}


def create_events(conn, settings, target_path: str, container: tuple | None = None) -> OperationResult:
    """Create events for the current Wwise selection under target_path.

    container: optional ("WorkUnit"|"Folder", name) created together with the
    events inside one WAAPI undo group, so a single Undo reverts everything.
    """
    result = OperationResult()

    objects = get_selected_objects(conn)
    # Events report isPlayable too, but Wwise rejects events targeting events
    if any(o.get("type") == "Event" for o in objects):
        result.error = "Selected objects are events — nothing can be created from them"
        return result

    selected = [o for o in objects if o.get("isPlayable")]
    if not selected:
        result.error = "No playable objects selected in Wwise"
        return result

    words_remove = settings.get("WORDS_REMOVE", [])
    loop_tokens = settings.get("SOUND_NAMING_FOR_LOOPS", [])
    naming_conv = settings.get("NAMING_CONVENTION", [])
    loop_suffix = settings.get("NAMING_FOR_LOOPS", "")
    stop_loops = settings.get("STOP_EVENT_FOR_LOOPS", False)
    seek_loops = settings.get("SEEK_ACTION_FOR_LOOPS", False)
    play_naming = settings.get("PLAY_NAMING_CONVENTION", "")
    stop_naming = settings.get("STOP_NAMING_CONVENTION", "")

    container_name = container[1] if container else None
    parent = container_name or target_path.strip("\\").split("\\")[-1]
    dest_path = f"{target_path}\\{container_name}" if container else target_path
    result.destination_path = dest_path

    existing = get_all_event_names(conn)

    set_args = {"objects": [], "onNameConflict": "merge"}
    planned = []          # event names in creation order
    seek_names = []

    for obj in selected:
        name, is_loop = clean_object_name(obj["name"], words_remove, loop_tokens, loop_suffix)
        children = []

        if is_loop and seek_loops:
            main_name = format_event_name(name, play_naming, settings, parent)
            payload = _build_seek(main_name, obj["id"], settings)
        else:
            main_name = format_event_name(name, play_naming, settings, parent)
            payload = _build_play(main_name, obj["id"], is_loop, settings)

        if main_name in existing:
            result.skipped.append(main_name)
        else:
            children.append(payload)
            planned.append(main_name)
            existing.add(main_name)
            if is_loop and seek_loops:
                seek_names.append(main_name)

        if is_loop and stop_loops:
            stop_name = format_event_name(name, stop_naming, settings, parent)
            if stop_name in existing:
                result.skipped.append(stop_name)
            else:
                children.append(_build_stop(stop_name, obj["id"], settings))
                planned.append(stop_name)
                existing.add(stop_name)

        if children:
            set_args["objects"].append({"object": dest_path, "children": children})

        result.incorrect_sources.extend(get_incorrect_sources(conn, obj["id"], naming_conv))

    if not set_args["objects"] and not container:
        result.error = "Nothing to create - all event names already exist"
        return result

    began = False
    try:
        conn.call("ak.wwise.core.undo.beginGroup")
        began = True
    except Exception:
        logger.warning("WAAPI undo group unavailable - operation will not be atomic", exc_info=True)

    try:
        if container:
            resp = conn.call("ak.wwise.core.object.create",
                             {"parent": target_path, "type": container[0], "name": container_name})
            kind = "workunit" if container[0] == "WorkUnit" else "folder"
            result.created.append(CreatedItem(kind, container_name, resp["id"]))

        if set_args["objects"]:
            conn.call("ak.wwise.core.object.set", set_args)

        # Enable seek randomizer on the freshly created Seek actions
        if seek_names:
            seek_min = settings.get("SEEK_RANDOM_MIN", 0.0)
            seek_max = settings.get("SEEK_RANDOM_MAX", 0.0)
            for seek_name in seek_names:
                q = {"waql": f'$ from type Action where actionType = 36 and parent.name = "{seek_name}"'}
                acts = conn.call("ak.wwise.core.object.get", q, options={"return": ["id"]})["return"]
                for a in acts:
                    conn.call("ak.wwise.core.object.setRandomizer", {
                        "object": str(a["id"]), "enabled": True,
                        "property": "SeekPercent", "min": seek_min, "max": seek_max,
                    })

        # Resolve ids of created events in one query (for click-to-select in the log)
        if planned:
            ids = {c["name"]: c["id"] for c in get_children(conn, dest_path)
                   if c.get("type") == "Event"}
            for name in planned:
                result.created.append(CreatedItem("event", name, ids.get(name, "")))
    finally:
        if began:
            try:
                conn.call("ak.wwise.core.undo.endGroup", {"displayName": "Create events"})
            except Exception:
                logger.exception("Failed to close WAAPI undo group")

    return result


def undo_last(conn, container_id: str = "") -> tuple:
    """Undo the whole last operation. Returns (ok, message).

    container_id: Work Unit / Folder created by that same operation, if any.
    """
    try:
        conn.call("ak.wwise.core.undo.undo")
    except Exception as e:
        logger.exception("Undo failed")
        return False, f"Undo failed ({e})"
    if container_id:
        _delete_if_empty(conn, container_id)
    return True, ""


def _delete_if_empty(conn, object_id: str) -> None:
    """Wwise does not undo Work Unit creation, so remove the container ourselves,
    but only when the undo left it empty (never delete content added later)."""
    try:
        children = get_children(conn, object_id)
    except Exception:
        return  # already gone (e.g. a Folder, whose creation Wwise does undo)
    if children:
        return
    try:
        conn.call("ak.wwise.core.object.delete", {"object": object_id})
    except Exception:
        logger.exception("Failed to delete container %s after undo", object_id)
