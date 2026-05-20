import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from utils.state import AppState

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("GitView")

    state = AppState()
    window = MainWindow(state)
    window.show()
    sys.exit(app.exec())