import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QSizePolicy, QScrollArea
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from git_backend.state import AppState
from utils.helper import *


class Sidebar(QWidget):
    """
    Single QTreeWidget with three collapsible group headers, Local Branches, Remote Branches and Tags.
    """

    branch_clicked = Signal(str) 

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
        hdr = QWidget()
        hdr.setStyleSheet(f"background:{BG_PANEL};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(14, 10, 14, 10)

        self._name_lbl   = label("No Repository", 14, TEXT_SECONDARY, 600)
        self._branch_dot = dot_badge(TEXT_TERTIARY)
        self._branch_lbl = label("—", 11, TEXT_TERTIARY)

        hl.addWidget(self._name_lbl)
        hl.addStretch()
        hl.addWidget(self._branch_dot)
        hl.addSpacing(4)
        hl.addWidget(self._branch_lbl)
        root.addWidget(hdr)
        root.addWidget(h_separator())

        # Single grouped QTreeWidget
        self._tree = QTreeWidget()
        self._tree.setObjectName("sidebarTree")
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setIndentation(16)
        self._tree.setAnimated(True)
        self._tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._tree.itemClicked.connect(self._on_item_clicked)

        # Pre-build the three permanent group headers
        self._grp_local   = self._make_group("Local Branches", "⎇")
        self._grp_remote  = self._make_group("Remote Branches", "⌥")
        self._grp_tags    = self._make_group("Tags", "◇")
        for grp in (self._grp_local, self._grp_remote, self._grp_tags):
            self._tree.addTopLevelItem(grp)
            grp.setExpanded(True)

        # Scrollable tree area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background:transparent; border:none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setStyleSheet(f"background:{BG_PANEL};")
        il = QVBoxLayout(inner)
        il.setContentsMargins(8, 4, 8, 8)
        il.setSpacing(0)
        il.addWidget(self._tree)

        scroll.setWidget(inner)
        root.addWidget(scroll)

        state.repo_changed.connect(self._on_repo_changed)



    # Slots
    def _on_repo_changed(self, repo):
        """Rebuild tree content whenever a repo is loaded or closed."""
        if repo is None:
            self._name_lbl.setText("No Repository")
            self._name_lbl.setStyleSheet(
                f"color:{TEXT_SECONDARY}; font-size:14px; font-weight:600; background:transparent;")
            self._branch_dot.setStyleSheet(f"background:{TEXT_TERTIARY}; border-radius:4px;")
            self._branch_lbl.setText("—")
            self._clear_groups()
            return

        # Update header strip
        name = os.path.basename(repo.working_dir)
        self._name_lbl.setText(name)
        self._name_lbl.setStyleSheet(
            f"color:{TEXT_PRIMARY}; font-size:14px; font-weight:600; background:transparent;")
        self._branch_dot.setStyleSheet(f"background:{ACCENT_GREEN}; border-radius:4px;")
        branch = self._state.active_branch
        self._branch_lbl.setText(branch)
        self._branch_lbl.setStyleSheet(
            f"color:{ACCENT_GREEN}; font-size:11px; background:transparent;")

        # Collect live data
        try:
            local = [b.name for b in repo.branches]
        except Exception:
            local = []

        try:
            # Flatten all remotes: each remote is its ref names ("origin/main")
            remote = []
            for r in repo.remotes:
                for ref in r.refs:
                    remote.append(ref.name)          # "origin/HEAD" ...
        except Exception:
            remote = []

        try:
            tags = [t.name for t in repo.tags]
        except Exception:
            tags = []

        self._populate(local, remote, tags)
        
        # Log
        self._state.logger.log(
            f"Sidebar populated: {len(local)} local, "
            f"{len(remote)} remote ref(s), {len(tags)} tag(s)"
        )


    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int):
        """Ignore group headers; emit branch_clicked for leaf items."""
        if item.parent() is None:
            return                             
        name = item.text(0)
        self.branch_clicked.emit(name)



    # Builders
    def _clear_groups(self):
        for grp in (self._grp_local, self._grp_remote, self._grp_tags):
            grp.takeChildren()



    def _populate(self, local: list, remote: list, tags: list):
        """Fill the three group headers with fresh child items."""
        self._clear_groups()
        active = self._state.active_branch

        # Local branches highlight the active one
        for name in local or ["(none)"]:
            is_active = (name == active)
            child = QTreeWidgetItem([name])
            f = QFont(); f.setBold(is_active)
            child.setFont(0, f)
            child.setForeground(0, QColor(ACCENT_GREEN if is_active else TEXT_SECONDARY))
            self._grp_local.addChild(child)

        # Remote branches
        for name in remote or ["(none)"]:
            child = QTreeWidgetItem([name])
            child.setForeground(0, QColor(TEXT_SECONDARY))
            self._grp_remote.addChild(child)

        # Tags
        for name in tags or ["(none)"]:
            child = QTreeWidgetItem([name])
            child.setForeground(0, QColor(ACCENT_ORANGE))
            self._grp_tags.addChild(child)



    @staticmethod
    def _make_group(title: str, icon: str) -> QTreeWidgetItem:
        """Create a non-selectable top-level group header item."""
        item = QTreeWidgetItem([f"  {icon}  {title}"])
        f = QFont(); f.setPointSize(11); f.setBold(True)

        item.setFont(0, f)
        item.setForeground(0, QColor(TEXT_TERTIARY))

        # Prevent the group header itself from being selected as a branch
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        return item
