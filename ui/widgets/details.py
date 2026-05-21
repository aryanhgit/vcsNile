from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea

from git_backend.state import AppState
from utils.helper import *


class DetailsPanel(QWidget):
    """"Shows metadata for the selected commit."""
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

        # Commit meta
        vbox.addWidget(label("Commit", 11, TEXT_TERTIARY, 600))
        self._sha_lbl = label("3f2e1d0a", 13, ACCENT)
        vbox.addWidget(self._sha_lbl)
        vbox.addWidget(h_separator())


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

        vbox.addWidget(label("Select a commit to inspect", 12, TEXT_TERTIARY))
        vbox.addStretch()

        scroll.setWidget(body)
        layout.addWidget(scroll)

        state.repo_changed.connect(self._on_repo_changed)

    def _on_repo_changed(self, repo):
        # Will be populated once the DAG canvas is wired
        pass
