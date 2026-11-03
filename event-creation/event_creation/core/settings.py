"""Persistent tool settings.

Stored as settings.json next to the exe (or in the project root when running
from source). DEFAULTS below defines both the starting values and the set of
recognised keys: anything else found in the file is ignored, and any key the
file is missing keeps its default, so older and newer config files both load.
"""
import json
import logging
import os

from ..paths import settings_path

logger = logging.getLogger(__name__)

DEFAULTS = {
    'NAMING_CONVENTION': [],
    'WORDS_REMOVE': [],
    'NAMING_FOR_LOOPS': '',
    'SOUND_NAMING_FOR_LOOPS': [],
    'WORDS_NOT_CAPITALIZE': [],
    'PLAY_NAMING_CONVENTION': '',
    'STOP_NAMING_CONVENTION': '',
    'INHERIT_NAME_FROM_PARENT': False,
    'STOP_EVENT_FOR_LOOPS': False,
    'LETTER_CASE_EVENT_NAME': None,
    'PLAY_LOOP_FADE_TIME': 0.0,
    'STOP_LOOP_FADE_TIME': 0.0,
    'SEEK_ACTION_FOR_LOOPS': False,
    'SEEK_Percent': 0.0,
    'SEEK_RANDOM_MIN': 0.0,
    'SEEK_RANDOM_MAX': 0.0,
    'WAAPI_URL': '',
}


class SettingsManager:
    def __init__(self, path: str | None = None):
        self.path = path or settings_path()
        self.settings = dict(DEFAULTS)
        self.load_error: str | None = None
        logger.info("Loading settings from: %s", self.path)
        self.load()

    def load(self):
        self.load_error = None
        try:
            if not os.path.exists(self.path):
                logger.info("Creating new settings file")
                self.save()
                return
            with open(self.path, 'r') as file:
                loaded = json.load(file)
            for key in self.settings:
                if key in loaded:
                    self.settings[key] = loaded[key]
            logger.info("Settings loaded successfully")
        except json.JSONDecodeError:
            self.load_error = "The settings file is corrupted or has incorrect format."
            logger.error(self.load_error)
        except Exception as e:
            self.load_error = f"Unexpected error loading settings: {e}"
            logger.exception("Settings load failed")

    def save(self):
        try:
            parent = os.path.dirname(self.path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(self.path, 'w') as file:
                json.dump(self.settings, file, indent=4)
        except Exception:
            logger.exception("Error saving settings")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()
