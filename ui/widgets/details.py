import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QListWidget, QTextEdit, QPushButton, QListWidgetItem
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, Signal

from git_backend.state import AppState
from utils.helper import label, h_separator
from ui.resources.theme import (ACCENT, BG_PANEL, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY)


class DetailsPanel(QWidget):
    """"Shows metadata for the selected commit."""
    
    # 1. Define the custom signal at the class level
    commit_selected = Signal(str)

    def __init__(self, state: AppState):
        super().__init__()
        self._state = state
        self.setObjectName("detailsPanel")
        self.setMinimumWidth(200)
        self.setMaximumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet(f"background: {BG_PANEL};")
        h = QHBoxLayout(header)
        h.setContentsMargins(14, 12, 14, 12)
        h.addWidget(label("Details", 13, TEXT_PRIMARY, 600))
        layout.addWidget(header)
        layout.addWidget(h_separator())

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        body = QWidget()
        body.setStyleSheet(f"background: {BG_PANEL};")
        vbox = QVBoxLayout(body)
        vbox.setContentsMargins(14, 10, 14, 10)
        vbox.setSpacing(6)

        # Commit meta (SHA)
        vbox.addWidget(label("Commit", 11, TEXT_TERTIARY, 600))
        self._sha_lbl = label("—", 13, ACCENT)
        # Make the SHA text selectable for easy copying
        self._sha_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse) 
        vbox.addWidget(self._sha_lbl)

        vbox.addSpacing(8)
        vbox.addWidget(h_separator())

        # Metadata (Author, Date, Branch)
        self._meta_labels: dict[str, QLabel] = {}
        for key in ("Author", "Date", "Branch"):
            row = QHBoxLayout()
            row.addWidget(label(key, 12, TEXT_TERTIARY))
            row.addStretch()
            val = label("—", 12, TEXT_PRIMARY)
            self._meta_labels[key] = val
            row.addWidget(val)
            vbox.addLayout(row)

        vbox.addSpacing(8)
        vbox.addWidget(h_separator())

        # Message
        vbox.addWidget(label("Message", 11, TEXT_TERTIARY, 600))
        self._msg_edit = QTextEdit()
        self._msg_edit.setReadOnly(True)
        self._msg_edit.setFixedHeight(70)
        # Optional: Give the text edit a subtle border so it doesn't look invisible
        self._msg_edit.setStyleSheet(f"color: {TEXT_PRIMARY}; border: 1px solid {TEXT_TERTIARY};")
        vbox.addWidget(self._msg_edit)

        vbox.addSpacing(8)
        vbox.addWidget(h_separator())

        # Parents
        vbox.addWidget(label("Parents", 11, TEXT_TERTIARY, 600))
        parents_row = QWidget()
        self._parents_layout = QHBoxLayout(parents_row)
        self._parents_layout.setContentsMargins(0, 0, 0, 0)
        self._parents_layout.setSpacing(6)
        self._parents_layout.setAlignment(Qt.AlignLeft)
        vbox.addWidget(parents_row)

        vbox.addSpacing(8)
        vbox.addWidget(h_separator())

        # Changed Files
        vbox.addWidget(label("Changed Files", 11, TEXT_TERTIARY, 600))
        self._files_list = QListWidget()
        self._files_list.setFixedHeight(140)
        vbox.addWidget(self._files_list)

        vbox.addStretch()

        scroll.setWidget(body)
        layout.addWidget(scroll)

        # Connect the signal to the handler
        self.commit_selected.connect(self.show_commit)

    def _clear_parents(self):
        """3. Memory-safe helper to clear parent buttons."""
        while self._parents_layout.count():
            item = self._parents_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def show_commit(self, sha: str):
        """Populate the details panel from a commit SHA (Step 3.5)."""
        repo = self._state.repo
        if repo is None:
            return

        try:
            commit = repo.commit(sha)
        except Exception:
            return

        # Full SHA
        self._sha_lbl.setText(sha[:12])
        self._sha_lbl.setToolTip(sha)

        # Author + date
        dt = datetime.datetime.fromtimestamp(commit.committed_date)
        self._meta_labels["Author"].setText(commit.author.name or commit.author.email)
        self._meta_labels["Date"].setText(dt.strftime("%Y-%m-%d %H:%M"))

        # Branch label — first matching branch name or "—"
        try:
            branch_names = [b.name for b in repo.branches if b.commit.hexsha == sha]
            self._meta_labels["Branch"].setText(branch_names[0] if branch_names else "—")
        except Exception:
            self._meta_labels["Branch"].setText("—")

        # Full commit message
        self._msg_edit.setPlainText(commit.message.strip())

        # Parents as clickable SHA links
        self._clear_parents()
        for parent in commit.parents:
            btn = QPushButton(parent.hexsha[:12])
            btn.setFlat(True)
            btn.setStyleSheet(f"color:{ACCENT}; font-family:monospace; border:none; padding:0;")
            btn.setCursor(Qt.PointingHandCursor)
            
            # Emit the signal instead of calling the function directly.
            # checked=False ignores the default boolean sent by clicked.
            btn.clicked.connect(lambda checked=False, p=parent.hexsha: self.commit_selected.emit(p))
            self._parents_layout.addWidget(btn)

        # Changed files from stats
        self._files_list.clear()
        try:
            for path, stat in commit.stats.files.items():
                # Use .get() to prevent KeyErrors if a stat dict is malformed
                a = stat.get("insertions", 0)
                d = stat.get("deletions", 0)
                item = QListWidgetItem(f"+{a} −{d}  {path}")
                item.setForeground(QColor(TEXT_SECONDARY))
                self._files_list.addItem(item)
        except Exception:
            pass