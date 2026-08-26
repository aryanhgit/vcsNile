import os

from PySide6.QtCore import QSettings

from ui.resources.constants import MAX_RECENT


class RecentRepos:
    """Persist a capped MRU list of repository paths."""

    _KEY = "recentRepos"

    def __init__(self):
        self._settings = QSettings("GitView", "GitView")

    def all(self) -> list:
        raw = self._settings.value(self._KEY, [])
        if isinstance(raw, str):
            raw = [raw]
        elif not isinstance(raw, list):
            raw = []
        return [path for path in raw if os.path.isdir(path)]

    def push(self, path: str):
        path = os.path.normpath(path)
        paths = self.all()
        if path in paths:
            paths.remove(path)
        paths.insert(0, path)
        self._settings.setValue(self._KEY, paths[:MAX_RECENT])

    def clear(self):
        self._settings.remove(self._KEY)
