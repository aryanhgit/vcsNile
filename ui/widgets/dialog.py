from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QDialog, QDialogButtonBox
from PySide6.QtCore  import Qt

from ui.resources.constants import *
from utils.helper import *

class InitRepoDialog(QDialog):
    """
    Shown when the chosen folder is not a Git repository.
    Asks: initialise here, or cancel.
    """

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Not a Git Repository")
        self.setFixedWidth(430)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(14)

        # Icon + title
        row = QHBoxLayout()
        row.addWidget(label("⚠", 28, ACCENT_ORANGE))
        row.addSpacing(8)
        row.addWidget(label("Not a Git Repository", 15, TEXT_PRIMARY, 600))
        row.addStretch()
        lay.addLayout(row)

        # Path + question
        short = path if len(path) < 54 else "…" + path[-52:]
        desc  = QLabel(
            f"<span style='color:{TEXT_SECONDARY}'><b>{short}</b></span>"
            f"<br><span style='color:{TEXT_TERTIARY}'>does not contain a Git repository.</span>"
            f"<br><br>Would you like to initialise one here?"
        )
        desc.setWordWrap(True)
        desc.setTextFormat(Qt.TextFormat.RichText)
        desc.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:13px; background:transparent;")
        lay.addWidget(desc)

        lay.addWidget(h_separator())

        # Buttons
        btns = QDialogButtonBox()
        btns.addButton("Initialise Here", QDialogButtonBox.ButtonRole.AcceptRole)
        btns.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)
