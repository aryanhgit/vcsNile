from PySide6.QtCore import QObject, Signal

from backend.logger import GitLogger


class AppState(QObject):
    """
    Single source of truth shared by every panel.
    """

    repo_changed = Signal(object)
    reset_preview_requested = Signal(str, str)
    reset_preview_cleared = Signal()

    revert_preview_requested  = Signal(str)
    revert_preview_cleared = Signal()

    reflog_entry_selected = Signal(str)

    commit_selected = Signal(object)

    def __init__(self):
        super().__init__()
        self._repo = None
        self.logger = GitLogger()

    @property
    def repo(self):
        return self._repo

    def set_repo(self, repo):
        self._repo = repo
        self.repo_changed.emit(repo)

    @property
    def repo_path(self) -> "str | None":
        return str(self._repo.working_dir) if self._repo else None

    @property
    def active_branch(self) -> str:
        if not self._repo:
            return "—"
        try:
            return self._repo.active_branch.name
        except TypeError:
            return self._repo.head.commit.hexsha[:7] + " (detached)"
