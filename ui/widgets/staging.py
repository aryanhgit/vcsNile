import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem
from PySide6.QtGui import QKeySequence, QShortcut, QBrush, QColor
from PySide6.QtCore import Qt, QSize

from git_backend.state import AppState
from utils.helper import *

# Staging column
class StagingColumn(QWidget):
    """
    A titled, scrollable column with a header, subtitle, and a QListWidget.
    """
    def __init__(self, title: str, subtitle: str,
                 action_label: str = "", action_color: str = TEXT_TERTIARY):
        super().__init__()
        self.setObjectName("stagingColumn")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Column header
        hdr = QWidget()
        hdr.setObjectName("stagingColHeader")
        hl  = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 10, 10, 10)
        hl.setSpacing(8)
        hl.addWidget(label(title, 13, TEXT_PRIMARY, 600))

        self._count_pill = label("0 files", 10, TEXT_TERTIARY)
        self._count_pill.setStyleSheet(
            f"color:{TEXT_TERTIARY}; font-size:10px;"
            f" background:{BG_BASE}; border-radius:3px; padding:1px 5px;"
        )
        hl.addWidget(self._count_pill)
        hl.addStretch()

        if action_label:
            act = QPushButton(action_label)
            act.setObjectName("stagingAction")
            act.setFixedHeight(22)
            act.setStyleSheet(
                f"color:{action_color}; background:{BG_HOVER};"
                " border:none; border-radius:4px; font-size:11px; padding:0 8px;"
            )
            hl.addWidget(act)

        root.addWidget(hdr)
        root.addWidget(h_separator())


        # Subtitle row
        sub_w = QWidget()
        sub_w.setStyleSheet(f"background:{BG_PANEL};")
        sl = QHBoxLayout(sub_w)
        sl.setContentsMargins(12, 4, 12, 4)

        sl.addWidget(label(subtitle, 11, TEXT_TERTIARY))
        root.addWidget(sub_w)
        root.addWidget(h_separator())


        # File list
        self._list = QListWidget()
        self._list.setObjectName("stagingList")
        self._list.setSpacing(1)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(self._list)


    # Public API
    def set_files(self, files: list):
        """
        Repopulate the list.
        files = [(full_path: str, status_char: str), ...]
        """

        self._list.clear()
        for full_path, status in files:
            badge, color, tooltip = STATUS_META.get(
                status, ("?", TEXT_TERTIARY, "unknown")
            )
            self._insert_item(full_path, badge, color, tooltip)

        n = len(files)
        self._count_pill.setText(f"{n} file{'s' if n != 1 else ''}")



    def clear_files(self):
        self._list.clear()
        self._count_pill.setText("0 files")



    # Private
    def _insert_item(self, full_path: str, badge: str, color: str, tooltip: str):
        """Build and attach a row widget: [badge pill] [filename / dir prefix]."""
        name     = os.path.basename(full_path)
        dir_part = os.path.dirname(full_path)

        row = QWidget()
        row.setStyleSheet("background:transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(10, 3, 10, 3)
        rl.setSpacing(8)

        # Coloured badge
        badge_lbl = QLabel(badge)
        badge_lbl.setFixedSize(18, 18)
        badge_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_lbl.setStyleSheet(
            f"color:white; background:{color}; border-radius:3px;"
            f" font-size:10px; font-weight:700;"
        )
        badge_lbl.setToolTip(tooltip)
        rl.addWidget(badge_lbl)


        # Filename + optional faint directory prefix
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
        self._list.addItem(item)
        self._list.setItemWidget(item, row)




class StagingWidget(QWidget):
    """
    Three-column staging view tracking Git status.
    """

    def __init__(self, state: AppState):
        super().__init__()
        self._state = state
        self._repo = None

        # Row Layout 
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Toolbar with refresh button 
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

        # Ctrl+R Shortcut
        shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        shortcut.activated.connect(self.refresh)

        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        root.addLayout(toolbar)

        # Column Layout 
        cols = QHBoxLayout()
        cols.setContentsMargins(0, 0, 0, 0)
        cols.setSpacing(0)

        self._col_wd   = StagingColumn("Working Directory", "Unstaged changes", "Stage All", ACCENT_GREEN)
        self._col_idx  = StagingColumn("Staging Area", "Index — ready to commit", "Unstage All", ACCENT_ORANGE)
        self._col_repo = StagingColumn("Local Repository", "HEAD commit tree", "", TEXT_TERTIARY)

        for i, col in enumerate((self._col_wd, self._col_idx, self._col_repo)):
            cols.addWidget(col)
            if i < 2:
                vline = QFrame()
                vline.setFrameShape(QFrame.Shape.VLine)
                vline.setStyleSheet(f"background:{SEPARATOR}; max-width:1px;")
                cols.addWidget(vline)

        root.addLayout(cols)

        # Connect repo to trigger an update 
        state.repo_changed.connect(self._on_repo_changed)


    def _on_repo_changed(self, repo):
        """Triggered via signal when user opens a new repository."""
        self._repo = repo
        self.refresh()

    
    def refresh(self):
        """
        Manually re-query and repopulate all three columns.
        """
        if self._repo is None:
            self._col_wd.clear_files()
            self._col_idx.clear_files()
            self._col_repo.clear_files()
            return
        
        # Working Directory (Unstaged & Untracked)
        wd_files = []
        try:
            # Unstaged modifications
            for d in self._repo.index.diff(None):
                code = d.change_type[0] if d.change_type else "M"
                wd_files.append((d.a_path, code))
                
            # Untracked files
            for path in self._repo.untracked_files:
                wd_files.append((path, "?"))
        except Exception:
            pass

        # Staging Area (Staged to Index)
        idx_files = []
        try:
            staged = self._repo.index.diff("HEAD")
            for d in staged:
                # Diff(HEAD) reverses direction, so we take the standard code mapping
                code = d.change_type[0] if d.change_type else "M"
                idx_files.append((d.a_path, code))
                
        except Exception:
            pass

        # Local Repository (HEAD commit tree)
        repo_files = []
        try:
            for item in self._repo.head.commit.tree.traverse():
                if item.type == "blob":
                    repo_files.append((item.path, "C"))
                
                # Limit parsing to 100
                if len(repo_files) >= 100:
                    break
        except Exception:
            pass

        # Feed the processed lists directly into our column widgets
        self._col_wd.set_files(wd_files)
        self._col_idx.set_files(idx_files)
        self._col_repo.set_files(repo_files)

        # Logging (safely checking if logger exists on state)
        if hasattr(self._state, "logger"):
            self._state.logger.log(
                f"Refreshed Staging: {len(wd_files)} unstaged, "
                f"{len(idx_files)} staged."
            )