"""Filesystem locations that differ between source checkout and frozen exe."""
import os
import sys
from pathlib import Path


def app_dir() -> Path:
    """Directory holding user-facing files (settings.json), next to the exe when frozen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[1]


def resource_dir() -> Path:
    """Directory holding bundled read-only assets (icons, fonts)."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parents[1]
    return base / "resources"


def settings_path() -> str:
    return os.path.join(str(app_dir()), "settings.json")
