from datetime import datetime

from PySide6.QtCore import QObject, Signal


class GitLogger(QObject):
    """
    Thin logging bus shared via AppState.
    Call state.logger.log("msg", level) from anywhere.
    Levels: INFO (default) · OK · WARN · ERR
    Emits message_logged(str) — LogPanel connects to this signal.
    """

    message_logged = Signal(str)

    def log(self, msg: str, level: str = "INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level:<4}] {msg}"
        self.message_logged.emit(line)
        print(line)
