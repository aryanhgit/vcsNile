from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter,
    QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QTabWidget, QTextEdit, QPlainTextEdit, QLineEdit, QFrame, QToolBar,
    QPushButton, QSizePolicy, QScrollArea, QListWidget, QListWidgetItem,
    QStackedWidget, QHeaderView,
    QRadioButton, QCheckBox, QButtonGroup, QComboBox,
    QGraphicsView, QGraphicsScene, QGraphicsItem,         # ← add
    QMenuBar, QMenu, QFileDialog, QMessageBox,
    QDialog, QDialogButtonBox,
)
from PySide6.QtCore import (
    Qt, QSize, QSettings, Signal, QObject,
    QPropertyAnimation, QEasingCurve, QPoint, QPointF,   # ← add
)
from PySide6.QtGui import (
    QFont, QColor, QAction, QKeySequence,
    QPainter, QPen, QBrush,                              # ← add
)

from ui.resources.theme import (ACCENT, ACCENT_GREEN, ACCENT_ORANGE, SEPARATOR, TEXT_SECONDARY, TEXT_TERTIARY)
from utils.helper import label
from utils.state import AppState

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



# ─────────────────────────────────────────────────────────────────────────────
# DAG canvas  (Phase 3 scaffold + Phase 4.2 HEAD animation)
# ─────────────────────────────────────────────────────────────────────────────

class HeadBadge(QWidget):
    """
    Floating overlay that represents the HEAD pointer on the DAG canvas.

    Rendered as a small pill sitting above the current HEAD commit node.
    Animated via QPropertyAnimation on its 'pos' Q_PROPERTY whenever HEAD
    moves — making the abstract concept of HEAD movement tangible.

    Mouse events are forwarded through (WA_TransparentForMouseEvents) so
    the badge never blocks clicks on the nodes beneath it.

        ┌──────────┐
        │  ◆ HEAD  │       ← this widget (parent = QGraphicsView)
        └────┬─────┘
             │  (NODE_R px gap)
             ●             ← commit circle drawn by QGraphicsScene
    """

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFixedSize(70, 24)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 0, 8, 0)
        lay.setSpacing(4)

        gem  = QLabel("◆")
        gem.setStyleSheet("color:white; font-size:9px; background:transparent;")
        text = QLabel("HEAD")
        text.setStyleSheet(
            "color:white; font-size:11px; font-weight:700; background:transparent;"
        )
        lay.addWidget(gem)
        lay.addWidget(text)

        self.setStyleSheet(
            f"background:{ACCENT_GREEN}; border-radius:5px;"
        )
        self.hide()


class DagCanvas(QGraphicsView):
    """
    Commit graph canvas — single-lane MVP for Phase 3 scaffold.

    Layout
    ------
    Each commit is a filled circle at (X=COL_X, Y=index×ROW_H).
    Edges are straight lines from child to parent.
    Branch/tag labels float to the right of the SHA abbreviation.

    HEAD badge (Step 4.2)
    ---------------------
    A HeadBadge widget is parented to the view (not the scene) so it
    floats on top and can be animated with QPropertyAnimation.

    Animation sequence
    ------------------
    1.  User selects a node  →  "Checkout here" overlay appears.
    2.  User clicks it       →  repo.git.checkout(sha).
    3.  state.set_repo()     →  _on_repo_changed fires.
    4.  _rebuild() redraws the scene with the new HEAD coloured.
    5.  _animate_badge() slides the badge from the old node to the new one.
    6.  finished signal      →  badge.raise_() to stay on top.
    """

    NODE_R = 9      # commit circle radius  (px)
    ROW_H  = 50     # vertical pitch between rows  (px)
    COL_X  = 48     # single-lane X centre  (px)
    MAX_C  = 120    # maximum commits to render

    def __init__(self, state: AppState):
        self._scene = QGraphicsScene()
        super().__init__(self._scene)
        self._state = state

        self.setObjectName("dagCanvas")
        self.setRenderHint(QPainter.Antialiasing)
        self.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        # sha → scene-space centre (QPointF)
        self._nodes: dict[str, QPointF] = {}
        self._head_sha: str | None = None     # where HEAD was before last change
        self._selected_sha: str | None = None

        # ── Floating overlays (parented to the view widget, not the scene) ────
        self._badge = HeadBadge(parent=self)

        self._co_btn = QPushButton("Checkout here", parent=self)
        self._co_btn.setObjectName("dagCheckoutBtn")
        self._co_btn.setFixedHeight(26)
        self._co_btn.hide()
        self._co_btn.clicked.connect(self._on_checkout_clicked)

        # ── QPropertyAnimation on QWidget.pos ────────────────────────────────
        self._anim = QPropertyAnimation(self._badge, b"pos")
        self._anim.setDuration(550)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.finished.connect(lambda: self._badge.raise_())

        self._scene.selectionChanged.connect(self._on_selection_changed)
        state.repo_changed.connect(self._on_repo_changed)

    # ── Repo change → rebuild + animate ──────────────────────────────────────

    def _on_repo_changed(self, repo):
        self._scene.clear()
        self._nodes.clear()
        self._co_btn.hide()
        self._selected_sha = None

        if repo is None:
            self._badge.hide()
            self._head_sha = None
            return

        try:
            new_sha = repo.head.commit.hexsha
        except Exception:
            new_sha = None

        self._rebuild(repo, new_sha)
        self._animate_badge(self._head_sha, new_sha)
        self._head_sha = new_sha

        # Re-connect after scene.clear() nuked the old connections
        self._scene.selectionChanged.connect(self._on_selection_changed)

    # ── Scene construction ────────────────────────────────────────────────────

    def _rebuild(self, repo, head_sha: "str | None"):
        """Draw commit nodes, edges, and branch/tag labels from GitPython data."""
        try:
            commits = list(repo.iter_commits("--all", max_count=self.MAX_C))
        except Exception:
            return

        if not commits:
            self._draw_empty_hint("Repository has no commits yet.")
            return

        # Build lookup tables
        branch_map: dict[str, list[str]] = {}
        tag_map:    dict[str, list[str]] = {}
        try:
            for b in repo.branches:
                branch_map.setdefault(b.commit.hexsha, []).append(b.name)
            for t in repo.tags:
                tag_map.setdefault(t.commit.hexsha, []).append(t.name)
        except Exception:
            pass

        # ── Pass 1: place nodes ───────────────────────────────────────────────
        for i, commit in enumerate(commits):
            x = float(self.COL_X)
            y = 20.0 + i * self.ROW_H
            self._nodes[commit.hexsha] = QPointF(x, y)
            self._draw_node(commit, x, y, head_sha, branch_map, tag_map)

        # ── Pass 2: draw edges ────────────────────────────────────────────────
        edge_pen = QPen(QColor(SEPARATOR), 1.5)
        for commit in commits:
            cx, cy = self._nodes[commit.hexsha].x(), self._nodes[commit.hexsha].y()
            for parent in commit.parents:
                if parent.hexsha in self._nodes:
                    px, py = (self._nodes[parent.hexsha].x(),
                              self._nodes[parent.hexsha].y())
                    self._scene.addLine(cx, cy + self.NODE_R,
                                        px, py - self.NODE_R, edge_pen)

        # Expand scene rect so the view scrolls correctly
        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-20, -20, 80, 40))

    def _draw_node(self, commit, x: float, y: float,
                   head_sha: "str | None",
                   branch_map: dict, tag_map: dict):
        sha      = commit.hexsha
        is_head  = (sha == head_sha)

        fill_col  = QColor(ACCENT_GREEN if is_head else ACCENT)
        ring_col  = fill_col.darker(130)
        r         = self.NODE_R

        # Circle — only circles are selectable
        ellipse = self._scene.addEllipse(
            x - r, y - r, r * 2, r * 2,
            QPen(ring_col, 1.5),
            QBrush(fill_col),
        )
        ellipse.setData(0, sha)
        ellipse.setFlag(QGraphicsItem.ItemIsSelectable, True)
        ellipse.setCursor(Qt.PointingHandCursor)

        mono = QFont()
        mono.setFamilies(["SF Mono", "Menlo", "Consolas"])
        mono.setPointSize(10)

        ui_font = QFont()
        ui_font.setPointSize(11)

        def _text(txt, color, font, px, py):
            t = self._scene.addText(txt, font)
            t.setDefaultTextColor(QColor(color))
            t.setPos(px, py)
            t.setAcceptedMouseButtons(Qt.NoButton)
            return t

        # Short SHA
        cursor_x = x + r + 8
        _text(sha[:7], TEXT_SECONDARY, mono, cursor_x, y - 9)
        cursor_x += 52

        # Branch labels (green pill-style)
        for name in branch_map.get(sha, []):
            item = _text(f" {name} ", ACCENT_GREEN, ui_font, cursor_x, y - 9)
            cursor_x += item.boundingRect().width() + 4

        # Tag labels (orange)
        for name in tag_map.get(sha, []):
            item = _text(f" {name} ", ACCENT_ORANGE, ui_font, cursor_x, y - 9)
            cursor_x += item.boundingRect().width() + 4

        # Commit message (truncated, tertiary colour)
        msg = commit.message.split("\n")[0][:52]
        _text(msg, TEXT_TERTIARY, ui_font, x + r + 8, y + 1)

    def _draw_empty_hint(self, msg: str):
        t = self._scene.addText(msg)
        t.setDefaultTextColor(QColor(TEXT_TERTIARY))
        t.setFont(QFont())
        t.setPos(40, 40)
        t.setAcceptedMouseButtons(Qt.NoButton)

    # ── HEAD badge animation ──────────────────────────────────────────────────

    def _animate_badge(self, old_sha: "str | None", new_sha: "str | None"):
        """
        Slide the HEAD badge from the old commit position to the new one.

        First load (old_sha is None)  →  place immediately, no animation.
        Same commit (no change)       →  no-op.
        Different commits             →  QPropertyAnimation over 550 ms.
        """
        if not new_sha or new_sha not in self._nodes:
            self._badge.hide()
            return

        end_pos = self._badge_pos_for(new_sha)

        if old_sha is None or old_sha not in self._nodes or old_sha == new_sha:
            # First paint — teleport, no animation
            self._badge.move(end_pos)
            self._badge.show()
            self._badge.raise_()
            return

        start_pos = self._badge_pos_for(old_sha)

        # Stop any in-flight animation before starting a new one
        if self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()

        self._badge.move(start_pos)
        self._badge.show()
        self._badge.raise_()

        self._anim.setStartValue(start_pos)
        self._anim.setEndValue(end_pos)
        self._anim.start()

    def _badge_pos_for(self, sha: str) -> QPoint:
        """View-space top-left corner for the badge centred above commit sha."""
        scene_pt  = self._nodes[sha]
        view_pt   = self.mapFromScene(scene_pt)
        return QPoint(
            view_pt.x() - self._badge.width() // 2,
            view_pt.y() - self._badge.height() - self.NODE_R - 4,
        )

    # ── Selection + checkout overlay ─────────────────────────────────────────

    def _on_selection_changed(self):
        selected = [i for i in self._scene.selectedItems() if i.data(0)]
        if not selected:
            self._selected_sha = None
            self._co_btn.hide()
            return

        sha = selected[0].data(0)
        if sha == self._head_sha:
            # HEAD is already here — no point offering checkout
            self._co_btn.hide()
            return

        self._selected_sha = sha
        scene_pt = self._nodes.get(sha)
        if scene_pt:
            view_pt = self.mapFromScene(scene_pt)
            self._co_btn.adjustSize()
            self._co_btn.move(
                view_pt.x() + self.NODE_R + 8,
                view_pt.y() - self._co_btn.height() // 2,
            )
            self._co_btn.show()
            self._co_btn.raise_()

    def _on_checkout_clicked(self):
        sha  = self._selected_sha
        repo = self._state.repo
        if not sha or repo is None:
            return

        self._co_btn.hide()
        self._state.logger.log(f"DAG checkout → {sha[:12]}")

        try:
            repo.git.checkout(sha)
            # set_repo re-emits repo_changed → _on_repo_changed → _animate_badge
            self._state.set_repo(repo)
            self._state.logger.log(f"Checked out {sha[:12]} (detached HEAD)", "OK  ")
        except Exception as exc:
            self._state.logger.log(f"Checkout failed: {exc}", "ERR ")

    # ── Overlay repositioning on resize ──────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep badge above the correct node after the view is resized
        if self._head_sha and self._head_sha in self._nodes:
            self._badge.move(self._badge_pos_for(self._head_sha))
        # Keep checkout button near the selected node
        if self._selected_sha and self._selected_sha in self._nodes:
            scene_pt = self._nodes[self._selected_sha]
            view_pt  = self.mapFromScene(scene_pt)
            self._co_btn.move(
                view_pt.x() + self.NODE_R + 8,
                view_pt.y() - self._co_btn.height() // 2,
            )