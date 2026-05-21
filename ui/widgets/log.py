from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit 

from utils.helper import *


class LogPanel(QWidget):
    """
    Collapsible bottom panel that displays every git operation.
    """

    # Maps level token
    _COLORS = {
        "INFO": TEXT_SECONDARY,
        "OK  ": ACCENT_GREEN,
        "WARN": ACCENT_ORANGE,
        "ERR ": ACCENT_RED,
    }

    # Pill labels
    _LABELS = {"INFO": "INFO", "OK  ": "OK", "WARN": "WARN", "ERR ": "ERR"}

    def __init__(self):
        super().__init__()
        self.setObjectName("logPanel")
        self.setMinimumHeight(28)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header strip
        hdr = QWidget()
        hdr.setObjectName("logHeader")
        hdr.setFixedHeight(28)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(10, 0, 8, 0)
        hl.setSpacing(6)

        self._toggle_btn = QPushButton("▾  Git Log")
        self._toggle_btn.setObjectName("logToggle")
        self._toggle_btn.setFlat(True)
        self._toggle_btn.clicked.connect(self.toggle)
        hl.addWidget(self._toggle_btn)
        hl.addStretch()

        # One pill per level, current shows running count
        self._pills: dict[str, tuple[QLabel, int]] = {}
        for key, color in self._COLORS.items():
            pill = label(f" {self._LABELS[key]} 0 ", 10, color, 500)
            pill.setStyleSheet(
                f"color:{color}; font-size:10px; font-weight:500;"
                f" background:{BG_BASE}; border-radius:3px; padding:1px 4px;"
            )
            self._pills[key] = (pill, 0)
            hl.addWidget(pill)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("logClear")
        clear_btn.setFixedHeight(20)
        clear_btn.clicked.connect(self._clear)
        hl.addWidget(clear_btn)

        root.addWidget(hdr)

        # Log body
        self._body = QPlainTextEdit()
        self._body.setObjectName("logOutput")
        self._body.setReadOnly(True)
        self._body.setMaximumBlockCount(2000)
        self._body.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        root.addWidget(self._body)

        self._expanded = True

    # Public API
    def append(self, line: str):
        """
        Append one formatted log line and auto-scroll.
        """
        # Identify level from the bracket token
        color = TEXT_SECONDARY
        for key, c in self._COLORS.items():
            if f"[{key}]" in line:
                color = c
                pill, count = self._pills[key]
                count += 1
                self._pills[key] = (pill, count)
                pill.setText(f" {self._LABELS[key]} {count} ")
                break

        # Timestamp dim
        ts_end = 10
        html = (
            f"<span style='color:{TEXT_TERTIARY}'>{line[:ts_end]}</span>"
            f"<span style='color:{color}'>{line[ts_end:]}</span>"
        )
        self._body.appendHtml(html)
        sb = self._body.verticalScrollBar()
        sb.setValue(sb.maximum())

    def toggle(self):
        """Collapse body to header-only strip, or restore it."""
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        self._toggle_btn.setText(
            "▾  Git Log" if self._expanded else "▸  Git Log"
        )

    # Private

    def _clear(self):
        self._body.clear()
        for key, (pill, _) in self._pills.items():
            self._pills[key] = (pill, 0)
            pill.setText(f" {self._LABELS[key]} 0 ")