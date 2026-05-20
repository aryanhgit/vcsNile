from PySide6.QtWidgets import QWidget, QHBoxLayout, QToolBar, QPushButton, QSizePolicy
from PySide6.QtCore import QSize

from utils.helper import *
from utils.state import AppState

class AppToolBar(QToolBar):
    def __init__(self, state: AppState):
        super().__init__()
        self._state = state
        self.setMovable(False)
        self.setIconSize(QSize(16, 16))

        for text in ("←", "→"):
            btn = QPushButton(text)
            btn.setFixedWidth(30)
            self.addWidget(btn)

        self.addSeparator()

        for text in ("Fetch", "Pull", "Push"):
            self.addWidget(QPushButton(text))

        # Push branch indicator to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)

        self._dot = dot_badge(TEXT_TERTIARY)
        self._branch_lbl = label("No repo", 13, TEXT_SECONDARY, 500)

        branch_row = QWidget()
        rl  = QHBoxLayout(branch_row)
        rl.setContentsMargins(0, 0, 4, 0)
        rl.setSpacing(6)
        rl.addWidget(self._dot)
        rl.addWidget(self._branch_lbl)
        self.addWidget(branch_row)

        state.repo_changed.connect(self._on_repo_changed)

    def _on_repo_changed(self, repo):
        if repo is None:
            self._dot.setStyleSheet(f"background:{TEXT_TERTIARY}; border-radius:4px;")
            self._branch_lbl.setText("No repo")
            self._branch_lbl.setStyleSheet(
                f"color:{TEXT_SECONDARY}; font-size:13px; background:transparent;")
        else:
            self._dot.setStyleSheet(f"background:{ACCENT_GREEN}; border-radius:4px;")
            self._branch_lbl.setText(self._state.active_branch)
            self._branch_lbl.setStyleSheet(
                f"color:{TEXT_PRIMARY}; font-size:13px; font-weight:500; background:transparent;")