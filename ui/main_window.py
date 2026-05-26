import os
from PySide6.QtWidgets import QMainWindow, QSplitter, QMenu, QFileDialog, QDialog, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence

from git_backend.recent_repos import RecentRepos
from git_backend.state import AppState
from ui.resources.theme import STYLESHEET
from ui.resources.constants import (BG_BASE, BG_PANEL, BG_HOVER, SEPARATOR, ACCENT, ACCENT_GREEN, ACCENT_RED, 
                                    ACCENT_ORANGE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY)
from ui.widgets.sidebar import Sidebar
from ui.widgets.central import CentralArea
from ui.widgets.details import DetailsPanel
from ui.widgets.dialog import InitRepoDialog
from ui.widgets.log import LogPanel
from ui.widgets.reset import TimeTravelPanel, ResetVisualizerPanel
from ui.widgets.revert import RevertWalkthroughPanel

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

        # Three-panel horizontal splitter
        h_split = QSplitter(Qt.Orientation.Horizontal)
        h_split.setHandleWidth(1)
        h_split.setChildrenCollapsible(False)

        self._sidebar = Sidebar(state) 
        h_split.addWidget(self._sidebar)
        h_split.addWidget(CentralArea(state))
        h_split.addWidget(DetailsPanel(state))

        h_split.setSizes([220, 760, 240])
        self.setCentralWidget(h_split)

        self._sidebar.branch_clicked.connect(
            lambda name: self.statusBar().showMessage(f"Branch: {name}", 4000)
        )
        self.statusBar().setStyleSheet(
            f"background:{BG_PANEL}; color:{TEXT_TERTIARY};"
            f" border-top:1px solid {SEPARATOR}; font-size:12px;"
        )

        state.repo_changed.connect(self._on_repo_changed)

        # Vertical splitter: main panels on top, log panel on bottom
        self._log_panel = LogPanel()
        state.logger.message_logged.connect(self._log_panel.append)

        v_split = QSplitter(Qt.Orientation.Vertical)
        v_split.setHandleWidth(1)
        v_split.addWidget(h_split)
        v_split.addWidget(self._log_panel)
        v_split.setCollapsible(0, False)
        v_split.setCollapsible(1, True)
        v_split.setSizes([560, 180])

        self._build_menu()
        self._time_travel = TimeTravelPanel(state, parent=self)

        self.setCentralWidget(v_split)

        self._reset_vis = ResetVisualizerPanel(state, parent=self)
        self._revert_walk = RevertWalkthroughPanel(state, parent=self)


    def _open_revert_walkthrough(self):
        self._revert_walk.show()
        self._revert_walk.raise_()
        self._revert_walk.activateWindow()


    def _open_reset_visualizer(self):
        self._reset_vis.show()
        self._reset_vis.raise_()
        self._reset_vis.activateWindow()


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

        # Git menu
        gm = mb.addMenu("Git")

        tt_act = QAction("Time Travel…", self)
        tt_act.setShortcut(QKeySequence("Ctrl+T"))
        tt_act.triggered.connect(self._open_time_travel)
        gm.addAction(tt_act)

        rv_act = QAction("Reset Visualizer…", self)
        rv_act.triggered.connect(self._open_reset_visualizer)
        gm.addAction(rv_act)

        rv2_act = QAction("Revert Walkthrough…", self)
        rv2_act.triggered.connect(self._open_revert_walkthrough)
        gm.addAction(rv2_act)
        
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

        vm = mb.addMenu("View")
   
        vm.addSeparator()
        toggle_log = QAction("Toggle Log Panel", self)
        toggle_log.setShortcut(QKeySequence("Ctrl+Shift+L"))
        toggle_log.triggered.connect(self._log_panel.toggle)
        vm.addAction(toggle_log)

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
            act = QAction(f"{name}    {short}", self)
            act.triggered.connect(lambda checked=False, p=path: self._load_repo(p))
            self._recent_menu.addAction(act)


    # Repository loading
    def _open_dialog(self):
        """Present a folder-picker then attempt to load the chosen directory."""
        start = self._state.repo_path or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(
            self, "Open Repository", start,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )
        if path:
            self._load_repo(path)


    def _load_repo(self, path: str):
        """Load `path` as a Git repositoryand persist in recent list."""

        self._state.logger.log(f"Opening: {path}")
        try:
            repo = git.Repo(path, search_parent_directories=True)
            self._accept_repo(repo)

        except (InvalidGitRepositoryError, NoSuchPathError):
            self._state.logger.log(f"Not a git repo: {path}", "WARN")
            dlg = InitRepoDialog(path, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._init_repo(path)

        except Exception as exc:
            self._state.logger.log(f"Error: {exc}", "ERR ")
            self._alert("Could not open repository", str(exc))



    def _init_repo(self, path: str):
        """git init `path` and load it."""
        try:
            repo = git.Repo.init(path)
            self._state.logger.log(f"git init : {path}", "OK  ")
            self._accept_repo(repo)
        except Exception as exc:
            self._alert("Initialisation failed", str(exc))


   
    def _accept_repo(self, repo):
        """Commit loaded repo to AppState, log a summary, persist in recent list."""
        try:
            n_local  = len(list(repo.branches))
            n_tags   = len(list(repo.tags))
            n_remote = sum(len(list(r.refs)) for r in repo.remotes)
            self._state.logger.log(
                f"Loaded '{os.path.basename(repo.working_dir)}'"
                f" — {n_local} local branch(es)"
                f", {n_remote} remote ref(s)"
                f", {n_tags} tag(s)",
                "OK  ",
            )
        except Exception:
            pass

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
            self.statusBar().clearMessage()   


    def _open_time_travel(self):
        self._time_travel.show()
        self._time_travel.raise_()
        self._time_travel.activateWindow()
