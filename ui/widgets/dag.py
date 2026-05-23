from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, 
    QPushButton, QGraphicsView, QGraphicsScene, QGraphicsItem
)
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QPointF
)
from PySide6.QtGui import (
    QFont, QFontMetrics, QColor,
    QPainter, QPen, QBrush, QPainterPath,
)

from ui.resources.theme import (ACCENT, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED, SEPARATOR, TEXT_SECONDARY, TEXT_TERTIARY)
from utils.helper import label
from utils.state import AppState
from git_backend.dagmodel import DAGLayout


class HeadBadge(QWidget):
    """
    Floating overlay that represents the HEAD pointer on the DAG canvas.
    """

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
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
    Commit graph canvas.
    """

    NODE_R = 9
    ROW_H  = 50
    COL_X  = 48
    COL_W  = 28
    MAX_C  = 120

    LANE_PALETTE = [
        "#0A84FF",
        "#30D158",
        "#FF9F0A",
        "#BF5AF2",
        "#32ADE6",
        "#FF453A",
        "#FFD60A",
    ]

    def __init__(self, state: AppState):
        self._scene = QGraphicsScene()
        super().__init__(self._scene)
        self._state = state

        self.setObjectName("dagCanvas")
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        self._nodes: dict[str, QPointF] = {}
        self._head_sha: str | None = None
        self._selected_sha: str | None = None

        self._overlays: list = []                                          # ← add
        state.reset_preview_requested.connect(self._on_preview_reset)     # ← add
        state.reset_preview_cleared.connect(self._clear_overlays)         # ← add

        self._badge = HeadBadge(parent=self)

        self._co_btn = QPushButton("Checkout here", parent=self)
        self._co_btn.setObjectName("dagCheckoutBtn")
        self._co_btn.setFixedHeight(26)
        self._co_btn.hide()
        self._co_btn.clicked.connect(self._on_checkout_clicked)

        self._anim = QPropertyAnimation(self._badge, b"pos")
        self._anim.setDuration(550)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.finished.connect(lambda: self._badge.raise_())

        self._scene.selectionChanged.connect(self._on_selection_changed)
        state.repo_changed.connect(self._on_repo_changed)


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
        self._head_sha = new_sha

        self._scene.selectionChanged.connect(self._on_selection_changed)


    def _rebuild(self, repo, head_sha: "str | None"):
        try:
            nodes, col_count = DAGLayout().build(repo)
        except Exception:
            return

        if not nodes:
            self._draw_empty_hint("Repository has no commits yet.")
            return

        col_colors: dict[int, QColor] = {
            c: QColor(self.LANE_PALETTE[c % len(self.LANE_PALETTE)])
            for c in range(col_count)
        }

        for node in nodes:
            x = float(self.COL_X + node.x * self.COL_W)
            y = 20.0 + node.y * self.ROW_H
            self._nodes[node.sha] = QPointF(x, y)
            self._draw_node_from(node, x, y, head_sha, col_colors)

        self._draw_edges(nodes, col_colors)

        self._scene.setSceneRect(
            self._scene.itemsBoundingRect().adjusted(-20, -20, 120, 40)
        )

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
        ellipse.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        ellipse.setCursor(Qt.CursorShape.PointingHandCursor)

        mono = QFont()
        mono.setFamilies(["SF Mono", "Menlo", "Consolas"])
        mono.setPointSize(10)

        ui_font = QFont()
        ui_font.setPointSize(11)

        def _text(txt, color, font, px, py):
            t = self._scene.addText(txt, font)
            t.setDefaultTextColor(QColor(color))
            t.setPos(px, py)
            t.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            return t

        cursor_x = x + r + 8
        _text(sha[:7], TEXT_SECONDARY, mono, cursor_x, y - 9)
        cursor_x += 52

        # Branch labels
        for name in branch_map.get(sha, []):
            item = _text(f" {name} ", ACCENT_GREEN, ui_font, cursor_x, y - 9)
            cursor_x += item.boundingRect().width() + 4

        # Tag labels
        for name in tag_map.get(sha, []):
            item = _text(f" {name} ", ACCENT_ORANGE, ui_font, cursor_x, y - 9)
            cursor_x += item.boundingRect().width() + 4

        # Commit message
        msg = commit.message.split("\n")[0][:52]
        _text(msg, TEXT_TERTIARY, ui_font, x + r + 8, y + 1)

    def _draw_empty_hint(self, msg: str):
        t = self._scene.addText(msg)
        t.setDefaultTextColor(QColor(TEXT_TERTIARY))
        t.setFont(QFont())
        t.setPos(40, 40)
        t.setAcceptedMouseButtons(Qt.MouseButton.NoButton)


    def _draw_node_from(self, node, x: float, y: float, 
                        head_sha: "str | None", col_colors: dict):
        """Render one CommitNode: circle + SHA + message + label pills."""
        is_head   = (node.sha == head_sha)
        lane_col  = col_colors.get(node.x, QColor(ACCENT))

        if is_head:
            fill_col = QColor(ACCENT_GREEN)
            r        = self.NODE_R + 2
        else:
            fill_col = lane_col
            r        = self.NODE_R

        ring_col = fill_col.darker(150)

        ellipse = self._scene.addEllipse(
            x - r, y - r, r * 2, r * 2,
            QPen(ring_col, 1.5),
            QBrush(fill_col),
        )
        ellipse.setData(0, node.sha)
        ellipse.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        ellipse.setCursor(Qt.CursorShape.PointingHandCursor)
        ellipse.setZValue(2)

        mono = QFont()
        mono.setFamilies(["SF Mono", "Menlo", "Consolas"])
        mono.setPointSize(10)

        ui_font = QFont()
        ui_font.setPointSize(10)

        text_x = x + self.NODE_R + 10

        sha_t = self._scene.addText(node.short_sha, mono)
        sha_t.setDefaultTextColor(QColor(TEXT_SECONDARY))
        sha_t.setPos(text_x, y - 9)
        sha_t.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        sha_t.setZValue(3)

        cursor_x = text_x + 52
        

        for lbl_text in node.labels:
            if lbl_text == "HEAD":
                color = ACCENT
                display = "HEAD"
            elif lbl_text.startswith("tag: "):
                color   = ACCENT_ORANGE
                display = lbl_text[5:]
            else:
                color   = ACCENT_GREEN
                display = lbl_text.lstrip("\u25cf").strip()
            cursor_x = self._pill_badge(display, cursor_x, y - 1, color)

        msg_t = self._scene.addText(node.message[:56], ui_font)
        msg_t.setDefaultTextColor(QColor(TEXT_TERTIARY))
        msg_t.setPos(text_x, y + 2)
        msg_t.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        msg_t.setZValue(3)

    def _draw_edges(self, nodes: list, col_colors: dict):
        """
        Draw all parent edges.

        1.Same-column parent : Straight QGraphicsLineItem.
        2.Cross-column parent : cubic-bezier QGraphicsPathItem.
        """
        for node in nodes:
            if node.sha not in self._nodes:
                continue
            cp = self._nodes[node.sha]
            cx, cy = cp.x(), cp.y()

            lane_col = col_colors.get(node.x, QColor(SEPARATOR))
            pen = QPen(lane_col, 1.8)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)

            for p_sha, p_col in zip(node.parent_shas, node.parent_cols):
                if p_sha not in self._nodes:
                    continue
                pp = self._nodes[p_sha]
                px, py = pp.x(), pp.y()

                if node.x == p_col:
                    item = self._scene.addLine(
                        cx, cy + self.NODE_R,
                        px, py - self.NODE_R,
                        pen,
                    )
                else:
                    path = QPainterPath(QPointF(cx, cy + self.NODE_R))
                    mid_y = (cy + py) / 2.0
                    path.cubicTo(
                        QPointF(cx, mid_y),
                        QPointF(px, mid_y),
                        QPointF(px, py - self.NODE_R),
                    )
                    item = self._scene.addPath(path, pen)

                item.setZValue(1)

    def _pill_badge(self, text: str, x: float, y: float, color: str) -> float:
        """
        Draw a rounded-rect pill label at scene position (x, y-centre).
        """
        font = QFont()
        font.setPointSize(9)

        fm  = QFontMetrics(font)
        tw  = fm.horizontalAdvance(text)
        pw, ph = tw + 10, 15

        bg = QColor(color)
        bg.setAlpha(38)
        border = QColor(color)

        pill_path = QPainterPath()
        pill_path.addRoundedRect(x, y - ph / 2, pw, ph, ph / 2, ph / 2)

        pill = self._scene.addPath(pill_path, QPen(border, 0.9), QBrush(bg))
        pill.setZValue(3)
        pill.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        t = self._scene.addText(text, font)
        t.setDefaultTextColor(border)
        t.setPos(x + 5, y - ph / 2 + 0.5)
        t.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        t.setZValue(4)

        return x + pw + 4


    def _on_selection_changed(self):
        selected = [i for i in self._scene.selectedItems() if i.data(0)]
        if not selected:
            self._selected_sha = None
            self._co_btn.hide()
            return

        sha = selected[0].data(0)
        if sha == self._head_sha:
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
            self._state.set_repo(repo)
            self._state.logger.log(f"Checked out {sha[:12]} (detached HEAD)", "OK  ")
        except Exception as exc:
            self._state.logger.log(f"Checkout failed: {exc}", "ERR ")


    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._selected_sha and self._selected_sha in self._nodes:
            scene_pt = self._nodes[self._selected_sha]
            view_pt  = self.mapFromScene(scene_pt)
            self._co_btn.move(
                view_pt.x() + self.NODE_R + 8,
                view_pt.y() - self._co_btn.height() // 2,
            )


    def _on_preview_reset(self, target_sha: str, mode: str):
        """
        Overlay visual rings on the DAG to preview which commits would be
        removed by a reset to target_sha.

        Red ring   = commit removed from branch (unreachable after reset).
        Orange ring = target commit (becomes the new HEAD / branch tip).

        Does NOT modify the scene's permanent nodes — overlays sit at
        z-value 10 and are removed by _clear_overlays().
        """
        self._clear_overlays()
        repo = self._state.repo
        if repo is None:
            return

        # Commits strictly between HEAD and target (exclusive of target itself)
        try:
            head_sha   = repo.head.commit.hexsha
            to_remove  = [
                c.hexsha
                for c in repo.iter_commits(f"{target_sha}..{head_sha}")
            ]
        except Exception:
            return

        r = self.NODE_R + 5

        # Red semi-transparent ring over each commit being removed
        red_fill   = QColor(255, 69,  58,  50)
        red_border = QColor(ACCENT_RED)
        for sha in to_remove:
            if sha in self._nodes:
                c    = self._nodes[sha]
                item = self._scene.addEllipse(
                    c.x() - r, c.y() - r, r * 2, r * 2,
                    QPen(red_border, 2.5),
                    QBrush(red_fill),
                )
                item.setZValue(10)
                self._overlays.append(item)

        # Orange ring on target — marks where branch will land
        if target_sha in self._nodes:
            c    = self._nodes[target_sha]
            item = self._scene.addEllipse(
                c.x() - r, c.y() - r, r * 2, r * 2,
                QPen(QColor(ACCENT_ORANGE), 2.5),
                QBrush(QColor(255, 159, 10, 40)),
            )
            item.setZValue(10)
            self._overlays.append(item)

    def _clear_overlays(self):
        """Remove all preview overlay items from the scene without rebuilding it."""
        for item in self._overlays:
            self._scene.removeItem(item)
        self._overlays.clear()