import os
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QSizePolicy, QMenu, QLabel
)

from git_backend.state import AppState
from ui.resources.constants import (
    ACCENT, ACCENT_GREEN, ACCENT_ORANGE, BG_BASE,
    BG_HOVER, BG_PANEL, STATUS_META, TEXT_PRIMARY, TEXT_TERTIARY,
)
from utils.helper import h_separator, label


class StagingColumn(QWidget):
    file_action_requested = Signal(str, str)

    def __init__(self, title: str, subtitle: str, action_label: str = "", 
                 action_color: str = TEXT_TERTIARY, context_menu_action: str = ""):
        super().__init__()
        self._context_menu_action = context_menu_action
        self._action_mode = context_menu_action
        self._files: list[tuple[str, str]] = []

        self.setObjectName("stagingColumn")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QWidget()
        header.setObjectName("stagingColHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 10, 10)
        header_layout.setSpacing(8)
        header_layout.addWidget(label(title, 13, TEXT_PRIMARY, 600))

        self._count_pill = label("0 files", 10, TEXT_TERTIARY)
        self._count_pill.setStyleSheet(
            f"color:{TEXT_TERTIARY}; font-size:10px;"
            f" background:{BG_BASE}; border-radius:3px; padding:1px 5px;"
        )
        header_layout.addWidget(self._count_pill)
        header_layout.addStretch()

        if action_label:
            self._action_button = QPushButton(action_label)
            self._action_button.setObjectName("stagingAction")
            self._action_button.setFixedHeight(22)
            self._action_button.setStyleSheet(
                f"color:{action_color}; background:{BG_HOVER};"
                " border:none; border-radius:4px; font-size:11px; padding:0 8px;"
            )
            header_layout.addWidget(self._action_button)

        root.addWidget(header)
        root.addWidget(h_separator())

        sub_w = QWidget()
        sub_w.setStyleSheet(f"background:{BG_PANEL};")
        sl = QHBoxLayout(sub_w)
        sl.setContentsMargins(12, 4, 12, 4)

        sl.addWidget(label(subtitle, 11, TEXT_TERTIARY))
        root.addWidget(sub_w)
        root.addWidget(h_separator())

        self._list = QListWidget()
        self._list.setObjectName("stagingList")
        self._list.setSpacing(1)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        if context_menu_action:
            self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self._list.customContextMenuRequested.connect(self._on_context_menu)
        root.addWidget(self._list)

    def set_files(self, files: list):
        self._files = list(files)
        self._list.clear()

        for full_path, status in files:
            badge, color, tooltip = STATUS_META.get(
                status, ("?", TEXT_TERTIARY, "unknown")
            )
            self._insert_item(full_path, badge, color, tooltip)

        n = len(files)
        self._count_pill.setText(f"{n} file{'s' if n != 1 else ''}")

    def clear_files(self):
        self._files = []
        self._list.clear()
        self._count_pill.setText("0 files")

    def _insert_item(self, full_path: str, badge: str, color: str, tooltip: str):
        name = os.path.basename(full_path)
        dir_part = os.path.dirname(full_path)

        row = QWidget()
        row.setStyleSheet("background:transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(10, 3, 10, 3)
        rl.setSpacing(8)

        badge_lbl = QLabel(badge)
        badge_lbl.setFixedSize(18, 18)
        badge_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_lbl.setStyleSheet(
            f"color:white; background:{color}; border-radius:3px;"
            f" font-size:10px; font-weight:700;"
        )
        badge_lbl.setToolTip(tooltip)
        rl.addWidget(badge_lbl)

        if dir_part:
            html = (
                f"<span style='color:{TEXT_PRIMARY};font-size:12px;'>{name}</span>"
                f"<br><span style='color:{TEXT_TERTIARY};font-size:10px;'>{dir_part}</span>"
            )
            row_h = 42
        else:
            html  = f"<span style='color:{TEXT_PRIMARY};font-size:12px;'>{name}</span>"
            row_h = 30

        name_lbl = QLabel(html)
        name_lbl.setTextFormat(Qt.TextFormat.RichText)
        name_lbl.setStyleSheet("background:transparent;")
        rl.addWidget(name_lbl)
        rl.addStretch()

        item = QListWidgetItem()
        item.setSizeHint(QSize(0, row_h))
        item.setToolTip(full_path)
        item.setData(Qt.ItemDataRole.UserRole, full_path)
        self._list.addItem(item)
        self._list.setItemWidget(item, row)

    def _on_context_menu(self, pos):
        item = self._list.itemAt(pos)
        if item is None:
            return

        path = item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return

        menu = QMenu(self)

        if self._context_menu_action == "stage":
            action_lbl = "Stage file" 
        else:
            action_lbl = "Unstage file"

        action = menu.addAction(action_lbl)
        action.setToolTip(path)

        font = action.font()
        action.setFont(font)

        chosen = menu.exec(self._list.mapToGlobal(pos))
        if chosen is action:
            self.file_action_requested.emit(path, self._context_menu_action)


class StagingWidget(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self._state = state
        self._repo = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(10, 10, 10, 10)
        
        refresh_btn = QPushButton("⟳  Refresh")
        refresh_btn.setFixedHeight(26)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #2c2c2e; color: #ebebf5;
                border: 1px solid #3a3a3c; border-radius: 6px;
                padding: 0 10px; font: 12px 'SF Pro Text';
            }
            QPushButton:hover  { background: #3a3a3c; }
            QPushButton:pressed{ background: #1c1c1e; }
        """)
        refresh_btn.clicked.connect(self.refresh)

        shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        shortcut.activated.connect(self.refresh)

        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        root.addLayout(toolbar)

        cols = QHBoxLayout()
        cols.setContentsMargins(0, 0, 0, 0)
        cols.setSpacing(0)

        self._col_wd   = StagingColumn("Working Directory", "Unstaged changes", "Stage All", ACCENT_GREEN, context_menu_action="stage")
        self._col_idx  = StagingColumn("Staging Area", "Index — ready to commit", "Unstage All", ACCENT_ORANGE, context_menu_action="unstage")
        self._col_repo = StagingColumn("Local Repository", "HEAD commit tree", "", TEXT_TERTIARY)
        
        cols.addWidget(self._col_wd)
        cols.addWidget(self._col_idx)
        cols.addWidget(self._col_repo)

        root.addLayout(cols)

        self._col_wd.file_action_requested.connect(self._on_file_action)
        self._col_idx.file_action_requested.connect(self._on_file_action)

        state.repo_changed.connect(self._on_repo_changed)
        self.refresh()

    def _on_repo_changed(self, repo):
        self._repo = repo
        self.refresh()

    def _on_file_action(self, path: str, action: str):
        if action == "stage":
            self._stage_file(path)
        elif action == "unstage":
            self._unstage_file(path)

    def _stage_file(self, path: str):
        repo = self._state.repo
        if repo is None:
            return
        if not os.path.exists(os.path.join(repo.working_dir, path)):
            self._state.logger.log(f"Stage aborted — path not found: {path}", "WARN")
            return
        try:
            repo.index.add([path])
            self._state.logger.log(f"Staged: {path}", "OK  ")
        except Exception as exc:
            self._state.logger.log(f"Stage failed ({path}): {exc}", "ERR ")
        finally:
            self.refresh()

    def _unstage_file(self, path: str):
        repo = self._state.repo
        if repo is None:
            return
        try:
            repo.index.reset(paths = [path])
            self._state.logger.log(f"Unstaged: {path}", "WARN")
        except Exception as exc:
            self._state.logger.log(f"Unstage failed ({path}): {exc}", "ERR ")
        finally:
            self.refresh()

    def refresh(self):
        if self._repo is None:
            self._col_wd.clear_files()
            self._col_idx.clear_files()
            self._col_repo.clear_files()
            return
        
        wd_files = []
        try:
            for d in self._repo.index.diff(None):
                code = d.change_type[0] if d.change_type else "M"
                wd_files.append((d.a_path, code))
                
            for path in self._repo.untracked_files:
                wd_files.append((path, "?"))
        except Exception:
            pass

        idx_files = []
        try:
            staged = self._repo.index.diff("HEAD")
            for d in staged:
                code = d.change_type[0] if d.change_type else "M"
                idx_files.append((d.a_path, code))
                
        except Exception:
            pass

        repo_files = []
        try:
            for item in self._repo.head.commit.tree.traverse():
                if item.type == "blob":
                    repo_files.append((item.path, "C"))
                
                if len(repo_files) >= 100:
                    break
        except Exception:
            pass

        self._col_wd.set_files(wd_files)
        self._col_idx.set_files(idx_files)
        self._col_repo.set_files(repo_files)

        if hasattr(self._state, "logger"):
            self._state.logger.log(
                f"Refreshed Staging: {len(wd_files)} unstaged, "
                f"{len(idx_files)} staged."
            )