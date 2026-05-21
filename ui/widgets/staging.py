import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, QSize

from git_backend.state import AppState
from utils.helper import *

# Staging column
class StagingColumn(QWidget):
    """
    A titled, scrollable QListWidget column with:
      - a header (title + live file-count pill + optional action button)
      - a subtitle line
      - per-item coloured badge (glyph) + filename + faint directory prefix
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
    Three-column staging view.
    """

    def __init__(self, state: AppState):
        super().__init__()
        self._state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        cols = QHBoxLayout()
        cols.setContentsMargins(0, 0, 0, 0)
        cols.setSpacing(0)

        self._col_wd   = StagingColumn(
            "Working Directory", "Unstaged changes", "Stage All",  ACCENT_GREEN,
        )
        self._col_idx  = StagingColumn(
            "Staging Area", "Index — ready to commit", "Unstage All", ACCENT_ORANGE,
        )
        self._col_repo = StagingColumn(
            "Local Repository", "HEAD commit tree", "", TEXT_TERTIARY ,
        )

        for i, col in enumerate((self._col_wd, self._col_idx, self._col_repo)):
            cols.addWidget(col)
            if i < 2:
                vline = QFrame()
                vline.setFrameShape(QFrame.Shape.VLine)
                vline.setStyleSheet(
                    f"background:{SEPARATOR}; max-width:1px;"
                )
                cols.addWidget(vline)

        root.addLayout(cols)
        state.repo_changed.connect(self._on_repo_changed)

    # Slot

    def _on_repo_changed(self, repo):
        if repo is None:
            self._col_wd.clear_files()
            self._col_idx.clear_files()
            self._col_repo.clear_files()
            return


        # Working Directory
        wd: list = []
        try:
            for d in repo.index.diff(None):          # index vs working tree
                wd.append((d.a_path, d.change_type))
        except Exception:
            pass
        try:
            for path in repo.untracked_files:
                wd.append((path, "?"))               # untracked
        except Exception:
            pass


        # Staging Area / Index
        idx: list = []
        try:
            for d in repo.index.diff("HEAD"):        # index vs last commit
                idx.append((d.a_path, d.change_type))
        except Exception:
            pass                                     # empty repo / no HEAD yet

       
        # Local Repository: blobs in the HEAD commit tree
        repo_files: list = []
        try:
            for item in repo.head.commit.tree.traverse():
                if item.type == "blob":
                    repo_files.append((item.path, "C"))
                if len(repo_files) >= 50:
                    break
        except Exception:
            pass

        self._col_wd.set_files(wd)
        self._col_idx.set_files(idx)
        self._col_repo.set_files(repo_files)

        self._state.logger.log(
            f"Staging tab: {len(wd)} unstaged, "
            f"{len(idx)} staged, "
            f"{len(repo_files)} committed file(s) shown"
        )