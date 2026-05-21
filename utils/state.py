from PySide6.QtCore  import Signal, QObject
from ui.widgets.staging import GitLogger

class AppState(QObject):
    """
    Single source of truth shared by every panel.
    Call set_repo() to load a repository; all subscribers are notified via the repo_changed signal automatically.
    """
    repo_changed = Signal(object)   

    def __init__(self):
        super().__init__()
        self._repo = None
        self.logger = GitLogger()

    # Public interface
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
