from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QSizePolicy
from PySide6.QtCore import Qt
from utils.helper import *

class DagPlaceholder(QWidget):
    """Stand-in for the DAG canvas (Phase 3: QGraphicsScene)."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        canvas = QFrame()
        canvas.setObjectName("canvas")
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        c_layout = QVBoxLayout(canvas)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ico = label("◆", 32, TEXT_TERTIARY)
        ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg = label("DAG Canvas", 15, TEXT_TERTIARY, 500)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = label("QGraphicsScene — Phase 3", 12, TEXT_TERTIARY)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        c_layout.addWidget(ico)
        c_layout.addWidget(msg)
        c_layout.addWidget(sub)
        layout.addWidget(canvas)