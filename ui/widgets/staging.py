from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame
from utils.helper import *

class StagingPlaceholder(QWidget):
    """Stand-in for the staging/unstage."""

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        for title, subtitle, dot_color in [
            ("Unstaged Changes", "Working directory", ACCENT_RED),
            ("Staged Changes", "Index / ready to commit", ACCENT_GREEN),
        ]:
            col = QFrame()
            col.setObjectName("canvas")
            col_lay = QVBoxLayout(col)
            col_lay.setContentsMargins(14, 14, 14, 14)
            col_lay.setSpacing(6)

            header_row = QHBoxLayout()
            header_row.addWidget(dot_badge(dot_color, 9))
            header_row.addSpacing(6)
            header_row.addWidget(label(title, 13, TEXT_PRIMARY, 600))
            header_row.addStretch()
            col_lay.addLayout(header_row)
            col_lay.addWidget(label(subtitle, 11, TEXT_TERTIARY))
            col_lay.addWidget(h_separator())
            col_lay.addStretch()
            layout.addWidget(col)