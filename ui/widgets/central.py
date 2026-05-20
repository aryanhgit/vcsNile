from PySide6.QtWidgets import QTabWidget
from utils.helper import *

from ui.widgets.dag import DagPlaceholder
from ui.widgets.staging import StagingPlaceholder
from ui.widgets.explorer import ObjectExplorer

class CentralArea(QTabWidget):
    def __init__(self):
        super().__init__()
        self.setDocumentMode(True)

        self.addTab(DagPlaceholder(), "Commit Graph")
        self.addTab(StagingPlaceholder(), "Staging")
        self.addTab(ObjectExplorer(), "Objects")