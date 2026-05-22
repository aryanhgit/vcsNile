from git_backend.state import AppState
from PySide6.QtWidgets import QTabWidget

from ui.widgets.dag import DagPlaceholder
from ui.widgets.staging import StagingWidget
from ui.widgets.explorer import ObjectExplorerTab
from ui.widgets.dag import DagCanvas

class CentralArea(QTabWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.setDocumentMode(True)

        self.addTab(DagCanvas(state), "Commit Graph")
        self.addTab(StagingWidget(state), "Staging")
        self.addTab(ObjectExplorerTab(state), "Objects")
