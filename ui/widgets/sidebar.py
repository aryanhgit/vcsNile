import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QSizePolicy, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from utils.helper import *
from utils.state import AppState

class Sidebar(QWidget):

    def __init__(self, state: AppState):
        super().__init__()
        self._state = state
        self.setObjectName("sidebar")
        self.setMinimumWidth(180)
        self.setMaximumWidth(280)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Repo name header
        header = QWidget()
        header.setStyleSheet(f"background:{BG_PANEL};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 10, 14, 10)

        self._name_lbl = label("No Repository", 14, TEXT_SECONDARY, 600)
        self._branch_dot = label(TEXT_TERTIARY)
        self._branch_lbl = label("—", 11, TEXT_TERTIARY)

        hl.addWidget(self._name_lbl)
        hl.addStretch()
        hl.addWidget(self._branch_dot)
        hl.addSpacing(4)
        hl.addWidget(self._branch_lbl)
        root.addWidget(header)
        root.addWidget(h_separator())

        # Scrollable tree area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background:transparent; border:none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._inner = QWidget()
        self._inner.setStyleSheet(f"background:{BG_PANEL};")
        self._vbox = QVBoxLayout(self._inner)
        self._vbox.setContentsMargins(8, 0, 8, 8)
        self._vbox.setSpacing(0)
        self._populate([], [], [])

        scroll.setWidget(self._inner)
        root.addWidget(scroll)

        state.repo_changed.connect(self._on_repo_changed)

    # ── Slot ──────────────────────────────────────────────────────────────────

    def _on_repo_changed(self, repo):
        if repo is None:
            self._name_lbl.setText("No Repository")
            self._name_lbl.setStyleSheet(
                f"color:{TEXT_SECONDARY}; font-size:14px; font-weight:600; background:transparent;")
            self._branch_dot.setStyleSheet(f"background:{TEXT_TERTIARY}; border-radius:4px;")
            self._branch_lbl.setText("—")
            self._populate([], [], [])
            return

        # Header
        name = os.path.basename(repo.working_dir)
        self._name_lbl.setText(name)
        self._name_lbl.setStyleSheet(
            f"color:{TEXT_PRIMARY}; font-size:14px; font-weight:600; background:transparent;")
        self._branch_dot.setStyleSheet(f"background:{ACCENT_GREEN}; border-radius:4px;")
        branch = self._state.active_branch
        self._branch_lbl.setText(branch)
        self._branch_lbl.setStyleSheet(
            f"color:{ACCENT_GREEN}; font-size:11px; background:transparent;")

        # Collect live data safely
        try:    branches = [b.name for b in repo.branches]
        except: branches = []

        try:    tags = [t.name for t in repo.tags]
        except: tags = []

        try:
            raw = repo.git.stash("list")
            stashes = [f"stash@{{{i}}}: {line.split(': ', 2)[-1]}"
                       for i, line in enumerate(raw.splitlines()) if line]
        except: stashes = []

        self._populate(branches, tags, stashes)

    # ── Builder ───────────────────────────────────────────────────────────────

    def _populate(self, branches: list, tags: list, stashes: list):
        # Clear existing widgets
        while self._vbox.count():
            item = self._vbox.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        active = self._state.active_branch

        # Branches
        self._vbox.addWidget(section_label("Branches"))
        b_rows = [(n, ACCENT_GREEN if n == active else TEXT_SECONDARY, n == active)
                  for n in branches] or [("—", TEXT_TERTIARY, False)]
        self._vbox.addWidget(self._make_tree(b_rows))

        # Tags
        self._vbox.addWidget(section_label("Tags"))
        t_rows = [(n, TEXT_SECONDARY, False) for n in tags] or [("No tags", TEXT_TERTIARY, False)]
        self._vbox.addWidget(self._make_tree(t_rows))

        # Stashes
        self._vbox.addWidget(section_label("Stashes"))
        s_rows = [(n, TEXT_SECONDARY, False) for n in stashes] or [("No stashes", TEXT_TERTIARY, False)]
        self._vbox.addWidget(self._make_tree(s_rows))

        self._vbox.addStretch()

    @staticmethod
    def _make_tree(rows: list) -> QTreeWidget:
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.setRootIsDecorated(False)
        tree.setIndentation(0)
        tree.setStyleSheet("background:transparent; border:none;")
        tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        for text, color, bold in rows:
            it = QTreeWidgetItem([text])
            f = QFont(); f.setBold(bold)
            it.setFont(0, f)
            it.setForeground(0, QColor(color))
            tree.addTopLevelItem(it)

        # Resize to content
        tree.setFixedHeight(len(rows) * 28 + 2)
        return tree

