from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem
from PySide6.QtCore import QSize

from utils.helper import *

class ObjectExplorer(QWidget):
    """Blob/tree/commit object browser."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        layout.addWidget(label("Object Explorer", 14, TEXT_PRIMARY, 600))
        layout.addWidget(label("Browse blobs, trees, and commits", 12, TEXT_TERTIARY))
        layout.addWidget(h_separator())

        lst = QListWidget()
        sample = [
            ("blob",   "a1b2c3d", "README.md"),
            ("blob",   "e4f5a6b", "main.py"),
            ("tree",   "9c8d7e6", "src/"),
            ("commit", "3f2e1d0", "Initial scaffold"),
            ("tree",   "b0a1c2d", "tests/"),
        ]
        type_colors = {"blob": ACCENT, "tree": ACCENT_ORANGE, "commit": ACCENT_GREEN}
        for kind, sha, name in sample:
            row_widget = QWidget()
            row_widget.setStyleSheet("background: transparent;")
            row_lay = QHBoxLayout(row_widget)
            row_lay.setContentsMargins(4, 2, 4, 2)
            row_lay.setSpacing(8)

            badge = label(kind, 10, type_colors.get(kind, TEXT_SECONDARY), 500)
            badge.setFixedWidth(44)
            sha_lbl = label(sha[:7], 12, TEXT_TERTIARY)
            name_lbl = label(name, 12, TEXT_PRIMARY)

            row_lay.addWidget(badge)
            row_lay.addWidget(sha_lbl)
            row_lay.addWidget(name_lbl)
            row_lay.addStretch()

            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 34))
            lst.addItem(item)
            lst.setItemWidget(item, row_widget)

        layout.addWidget(lst)