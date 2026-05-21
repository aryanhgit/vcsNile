from PySide6.QtWidgets import QTabWidget

from ui.widgets.dag import DagPlaceholder
from ui.widgets.staging import StagingWidget
from ui.widgets.explorer import ObjectExplorer

from utils.helper import *
from utils.state import AppState

class CentralArea(QTabWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.setDocumentMode(True)

        # self.addTab(
        #     _placeholder_tab("◆", "DAG Canvas", "QGraphicsScene"),
        #     "Commit Graph",
        # )

        self.addTab(DagPlaceholder(), "Commit Graph")
        self.addTab(StagingWidget(state), "Staging")
        self.addTab(ObjectExplorer(), "Objects")

        # self.addTab(
        #     _placeholder_tab("⬡", "Object Explorer", "Blobs, trees, commits — Phase 2"),
        #     "Objects",
        # )