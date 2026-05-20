from PySide6.QtWidgets import QMainWindow, QSplitter
from PySide6.QtCore import Qt

from ui.resources.theme import STYLESHEET
from utils.helper import *

from ui.widgets.sidebar import Sidebar
from ui.widgets.central import CentralArea
from ui.widgets.details import DetailsPanel
from ui.widgets.toolbar import AppToolBar

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitView")
        self.resize(1200, 740)
        self.setMinimumSize(800, 500)
        self.setStyleSheet(STYLESHEET)

        # Toolbar
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, AppToolBar())

        # Three-panel splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        splitter.addWidget(Sidebar())
        splitter.addWidget(CentralArea())
        splitter.addWidget(DetailsPanel())

        # Initial proportions: sidebar | central | details
        splitter.setSizes([220, 760, 240])

        self.setCentralWidget(splitter)