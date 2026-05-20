import os
from PySide6.QtWidgets import QMainWindow, QSplitter, QMenu, QFileDialog, QDialog, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence

from ui.resources.theme import STYLESHEET

from ui.widgets.sidebar import Sidebar
from ui.widgets.central import CentralArea
from ui.widgets.details import DetailsPanel
from ui.widgets.toolbar import AppToolBar
from ui.widgets.recents import RecentRepos
from ui.widgets.dialog import InitRepoDialog

from utils.state import AppState

import git
from git.exc import InvalidGitRepositoryError, NoSuchPathError

class MainWindow(QMainWindow):
    def __init__(self, state: AppState):
        super().__init__()
        self._state  = state
        self._recent = RecentRepos()

        self.setWindowTitle("GitView")
        self.resize(1200, 740)
        self.setMinimumSize(800, 500)
        self.setStyleSheet(STYLESHEET)

        self._build_menu()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, AppToolBar(state))

        # Three-panel splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        splitter.addWidget(Sidebar(state))
        splitter.addWidget(CentralArea())
        splitter.addWidget(DetailsPanel(state))

        splitter.setSizes([220, 760, 240])
        self.setCentralWidget(splitter)

        state.repo_changed.connect(self._on_repo_changed)


    # Menu bar
    def _build_menu(self):
        mb = self.menuBar()

        # File menu
        fm = mb.addMenu("File")

        open_act = QAction("Open Repository…", self)
        open_act.setShortcut(QKeySequence("Ctrl+O"))
        open_act.triggered.connect(self._open_dialog)
        fm.addAction(open_act)

        fm.addSeparator()

        # Recent Repositories sub-menu, rebuilt each time it's opened
        self._recent_menu = QMenu("Recent Repositories", self)
        self._recent_menu.aboutToShow.connect(self._rebuild_recent_menu)
        fm.addMenu(self._recent_menu)

        clear_act = QAction("Clear Recent Repositories", self)
        clear_act.triggered.connect(lambda: self._recent.clear())
        fm.addAction(clear_act)

        fm.addSeparator()

        close_act = QAction("Close Repository", self)
        close_act.setShortcut(QKeySequence("Ctrl+W"))
        close_act.triggered.connect(lambda: self._state.set_repo(None))
        fm.addAction(close_act)

        # View menu (stubs wired to central tabs later)
        vm = mb.addMenu("View")
        for title in ("Commit Graph", "Staging Area", "Object Explorer"):
            vm.addAction(QAction(title, self))

    def _rebuild_recent_menu(self):
        """Regenerate Recent Repositories entries each time the sub-menu opens."""
        self._recent_menu.clear()
        paths = self._recent.all()

        if not paths:
            empty = QAction("No recent repositories", self)
            empty.setEnabled(False)
            self._recent_menu.addAction(empty)
            return

        for path in paths:
            name  = os.path.basename(path)
            short = path if len(path) < 56 else "…" + path[-54:]
            act   = QAction(f"{name}    {short}", self)
            act.triggered.connect(lambda checked=False, p=path: self._load_repo(p))
            self._recent_menu.addAction(act)


    # Repository loading
    def _open_dialog(self):
        """Present a folder-picker then attempt to load the chosen directory."""
        start = self._state.repo_path or os.path.expanduser("~")
        path  = QFileDialog.getExistingDirectory(
            self, "Open Repository", start,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )
        if path:
            self._load_repo(path)

    def _load_repo(self, path: str):
        """Load `path` as a Git repositoryand persist in recent list."""

        try:
            repo = git.Repo(path, search_parent_directories=True)
            self._accept_repo(repo)

        except (InvalidGitRepositoryError, NoSuchPathError):
            # Ask user whether to initialise a fresh repository here
            dlg = InitRepoDialog(path, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._init_repo(path)

        except Exception as exc:
            self._alert("Could not open repository", str(exc))

    def _init_repo(self, path: str):
        """git init `path` and load it."""
        try:
            repo = git.Repo.init(path)
            self._accept_repo(repo)
        except Exception as exc:
            self._alert("Initialisation failed", str(exc))

    def _accept_repo(self, repo):
        """Commit the loaded repo to AppState and record it in recent list."""
        self._state.set_repo(repo)
        self._recent.push(str(repo.working_dir))
    
    def _alert(self, title: str, message: str):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(message)
        box.setIcon(QMessageBox.Icon.Warning)
        box.exec()


    def _on_repo_changed(self, repo):
        if repo:
            self.setWindowTitle(f"GitView | {os.path.basename(repo.working_dir)}")
        else:
            self.setWindowTitle("GitView")