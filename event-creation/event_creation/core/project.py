"""Read only queries against the Wwise project (WAQL) and UI commands."""
import logging

logger = logging.getLogger(__name__)

_RETURN = {"return": ["id", "name", "path", "type"]}


def get_targets(conn) -> list:
    """All Work Units and Folders in the Events category.
    Returns list of dicts: {id, name, path, type}."""
    items = []
    for waql in ('$ from type WorkUnit where category = "Events"',
                 '$ from type Folder where category = "Events"'):
        res = conn.call("ak.wwise.core.object.get", {"waql": waql}, options=_RETURN)
        items.extend(res.get("return", []))
    return items


def get_project_name(conn) -> str:
    info = conn.call("ak.wwise.core.getProjectInfo")
    return info.get("name", "Not Connected")


def get_selected_objects(conn) -> list:
    options = {"return": ["id", "name", "type", "isPlayable"]}
    return conn.call("ak.wwise.ui.getSelectedObjects", {}, options=options)["objects"]


def get_all_event_names(conn) -> set:
    """One query for every Event name in the project, used to skip duplicates."""
    res = conn.call("ak.wwise.core.object.get",
                    {"waql": '$ from type Event'},
                    options={"return": ["name"]})
    return {item["name"] for item in res.get("return", [])}


def get_children(conn, parent_path: str) -> list:
    res = conn.call("ak.wwise.core.object.get",
                    {"waql": f'$ "{parent_path}" select children'},
                    options=_RETURN)
    return res.get("return", [])


def get_incorrect_sources(conn, object_id: str, naming_convention: list) -> list:
    """Names of AudioFileSource descendants that match none of the configured tokens."""
    if not naming_convention:
        return []
    query = {"waql": f'$ "{object_id}" select this, descendants where type = "AudioFileSource"'}
    res = conn.call("ak.wwise.core.object.get", query, options={"return": ["name"]})
    return [src["name"] for src in res.get("return", [])
            if not any(tok in src["name"] for tok in naming_convention)]


def select_in_wwise(conn, object_id: str) -> None:
    conn.call("ak.wwise.ui.commands.execute", {
        "command": "FindInProjectExplorerSelectionChannel1",
        "objects": [object_id],
    })


def get_parent_path(full_path: str) -> str:
    parts = full_path.strip("\\").split("\\")
    if len(parts) <= 1:
        return ""
    return "\\".join([""] + parts[:-1])


def can_create_workunit(new_name: str, parent_path: str, targets: list) -> bool:
    """Validation against a cached target list (no WAAPI round- rip per keystroke).

    Work unit names must be unique among all Events work units; additionally no
    folder with the same name may exist in the same parent.
    """
    low = new_name.lower()
    for t in targets:
        if t["type"] == "WorkUnit" and t["name"].lower() == low:
            return False
        if t["type"] == "Folder" and t["name"].lower() == low \
                and get_parent_path(t["path"]) == parent_path:
            return False
    return True


def can_create_folder(new_name: str, parent_path: str, targets: list) -> bool:
    """No folder or work unit with the same name in the same parent."""
    low = new_name.lower()
    for t in targets:
        if t["name"].lower() == low and get_parent_path(t["path"]) == parent_path:
            return False
    return True
