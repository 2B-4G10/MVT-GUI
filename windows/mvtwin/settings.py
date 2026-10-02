"""The app's preferences, kept in settings.ini in the data folder so they
travel with the portable app."""

from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, Signal

from . import environment


class Settings(QObject):
    changed = Signal()

    _DEFAULTS = {
        "appearance": "system",  # system, light or dark
        "checkForUpdates": True,
        "checkIndicatorUpdates": True,
        "verbose": False,
        "resultsFolder": "",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        path = environment.data_folder() / "settings.ini"
        self._store = QSettings(str(path), QSettings.Format.IniFormat)

    def _get(self, key: str):
        default = self._DEFAULTS[key]
        value = self._store.value(key, default)
        if isinstance(default, bool):
            return value if isinstance(value, bool) else str(value).lower() == "true"
        return str(value)

    def _set(self, key: str, value) -> None:
        self._store.setValue(key, value)
        self._store.sync()
        self.changed.emit()

    appearance = property(
        lambda self: self._get("appearance"), lambda self, v: self._set("appearance", v)
    )
    check_updates = property(
        lambda self: self._get("checkForUpdates"),
        lambda self, v: self._set("checkForUpdates", v),
    )
    check_indicator_updates = property(
        lambda self: self._get("checkIndicatorUpdates"),
        lambda self, v: self._set("checkIndicatorUpdates", v),
    )
    verbose = property(
        lambda self: self._get("verbose"), lambda self, v: self._set("verbose", v)
    )
    results_folder = property(
        lambda self: self._get("resultsFolder"),
        lambda self, v: self._set("resultsFolder", v),
    )
