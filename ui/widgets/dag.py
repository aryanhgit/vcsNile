import time as _time

from PySide6.QtWidgets import (QPushButton, QGraphicsView, QGraphicsScene, QGraphicsItem
)
from PySide6.QtCore import (Qt, Signal, QPointF,)
from PySide6.QtGui import (
    QFont, QFontMetrics, QColor,
    QPainter, QPen, QBrush, QPainterPath,
)

from ui.resources.theme import (ACCENT, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED, SEPARATOR, TEXT_SECONDARY, TEXT_TERTIARY, TEXT_PRIMARY)
from utils.helper import label
from utils.state import AppState
from git_backend.dagmodel import DAGLayout

class DagCanvas(QGraphicsView):
    """
    Commit graph canvas.
    """

    commit_selected = Signal(str)

    NODE_R = 5
    ROW_H = 40
    HEADER_H = 36
    COL_X = 230
    COL_W = 20
    MSG_PAD  = 28 

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
        self.setStyleSheet("background: transparent; border: none;")

        self._nodes: dict[str, QPointF] = {}
        self._head_sha: str | None = None
        self._selected_sha: str | None = None
        self._overlays: list = []
        self._col_count: int = 1

        self._revert_ghost: list = []
        state.revert_preview_requested.connect(self._on_preview_revert)
        state.revert_preview_cleared.connect(self._clear_revert_preview)
        
        state.reflog_entry_selected.connect(self._on_reflog_entry_selected)

        state.reset_preview_requested.connect(self._on_preview_reset)
        state.reset_preview_cleared.connect(self._clear_overlays)

        self._co_btn = QPushButton("Checkout here", parent=self)
        self._co_btn.setObjectName("dagCheckoutBtn")
        self._co_btn.setFixedHeight(26)
        self._co_btn.hide()
        self._co_btn.clicked.connect(self._on_checkout_clicked)
            
        self._scene.selectionChanged.connect(self._on_selection_changed)
        state.repo_changed.connect(self._on_repo_changed)


    def _on_repo_changed(self, repo):
        self._scene.clear()
        self._nodes.clear()
        self._co_btn.hide()
        self._selected_sha = None

        if repo is None:
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
            self._col_count = max(1, col_count)
        except Exception:
            return

        if not nodes:
            self._draw_empty_hint("Repository has no commits yet.")
            return

        self._draw_headers()

        col_colors: dict[int, QColor] = {
            c: QColor(self.LANE_PALETTE[c % len(self.LANE_PALETTE)])
            for c in range(self._col_count)
        }

        for node in nodes:
            x = float(self.COL_X + node.x * self.COL_W)
            y = float(self.HEADER_H + self.ROW_H // 2) + node.y * self.ROW_H
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


    @staticmethod
    def _format_date(ts: int) -> str:
        """Return a compact relative or short-date string for a Unix timestamp."""
        diff = _time.time() - ts
        if diff < 60:          return "just now"
        if diff < 3_600:       return f"{int(diff // 60)}m ago"
        if diff < 86_400:      return f"{int(diff // 3_600)}h ago"
        if diff < 86_400 * 7:  return f"{int(diff // 86_400)}d ago"
        if diff < 86_400 * 30: return f"{int(diff // 86_400 // 7)}w ago"
        return _time.strftime("%b %d", _time.localtime(ts))


    def _msg_x(self) -> float:
        """Left edge of the commit-message text column dynamically clearing the graph lanes."""
        return float(self.COL_X + (self._col_count * self.COL_W) + self.MSG_PAD)
  

    def _draw_headers(self):
        """Column headers with a clean separator line underneath."""
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)

        hdr_color = QColor(TEXT_TERTIARY)

        def _hdr(txt: str, px: float):
            t = self._scene.addText(txt, font)
            t.setDefaultTextColor(hdr_color)
            t.setPos(px, 8)
            t.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            t.setZValue(10)

        _hdr("BRANCH / TAG", 10)
        _hdr("GRAPH", self.COL_X - 8)
        _hdr("COMMIT", self._msg_x())

        sep_col = QColor(SEPARATOR)
        sep_col.setAlpha(70)
        sep = self._scene.addLine(0, self.HEADER_H, 8000, self.HEADER_H, QPen(sep_col, 1.0))
        sep.setZValue(9)


    def _draw_node_from(self, node, x: float, y: float,
                        head_sha: "str | None", col_colors: dict):
        is_head  = (node.sha == head_sha)
        lane_col = col_colors.get(node.x, QColor(ACCENT))
        mx       = self._msg_x()

        if is_head:
            bg = QColor(lane_col); bg.setAlpha(20)
        elif node.y % 2 == 0:
            bg = QColor(255, 255, 255, 6)
        else:
            bg = None

        if bg is not None:
            hl = self._scene.addRect(
                0, y - self.ROW_H / 2,
                8000, self.ROW_H,
                QPen(Qt.PenStyle.NoPen), QBrush(bg),
            )
            hl.setZValue(-5)

        sep_col = QColor(SEPARATOR); sep_col.setAlpha(25)
        sep = self._scene.addLine(
            0, y + self.ROW_H / 2,
            8000, y + self.ROW_H / 2,
            QPen(sep_col, 0.5),
        )
        sep.setZValue(-4)

        lbl_x = 10.0
        for lbl_text in node.labels:
            if lbl_text == "HEAD":
                continue
            is_active = "\u25cf" in lbl_text
            display = lbl_text.replace("\u25cf", "✓").strip() if is_active else lbl_text.strip()
            is_tag  = display.startswith("tag:")
            color   = QColor(ACCENT_ORANGE) if is_tag else lane_col
            if is_tag:
                display = display[4:].strip()
            lbl_x = self._pill_badge(display, lbl_x, y, color, is_active)
            lbl_x += 5

        if lbl_x > 10:
            dot_pen = QPen(lane_col, 1.0, Qt.PenStyle.DotLine)
            dot_pen.setDashPattern([1, 3])
            conn = self._scene.addLine(lbl_x, y, x - self.NODE_R - 2, y, dot_pen)
            conn.setZValue(1)

        r = self.NODE_R

        if is_head:
            ring_col = QColor(lane_col); ring_col.setAlpha(70)
            ring = self._scene.addEllipse(
                x - r - 4, y - r - 4, (r + 4) * 2, (r + 4) * 2,
                QPen(ring_col, 1.5),
                QBrush(Qt.GlobalColor.transparent),
            )
            ring.setZValue(4)

        ellipse = self._scene.addEllipse(
            x - r, y - r, r * 2, r * 2,
            QPen(Qt.PenStyle.NoPen),
            QBrush(lane_col),
        )
        ellipse.setData(0, node.sha)
        ellipse.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        ellipse.setCursor(Qt.CursorShape.PointingHandCursor)
        ellipse.setZValue(5)

        msg_font = QFont()
        msg_font.setPointSize(10)
        if is_head:
            msg_font.setBold(True)

        msg_t = self._scene.addText(node.message[:70], msg_font)
        msg_h = msg_t.boundingRect().height()
        msg_t.setDefaultTextColor(QColor(TEXT_PRIMARY if is_head else TEXT_SECONDARY))
        msg_t.setPos(mx, y - msg_h + 3)
        msg_t.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        msg_t.setZValue(3)

        meta_font = QFont()
        meta_font.setPointSize(8)

        meta = f"{node.author[:28]}  ·  {node.short_sha}  ·  {self._format_date(node.date)}"
        meta_t = self._scene.addText(meta, meta_font)
        meta_t.setDefaultTextColor(QColor(TEXT_TERTIARY))
        meta_t.setPos(mx, y + 4)
        meta_t.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        meta_t.setZValue(3)


    def _draw_edges(self, nodes: list, col_colors: dict):
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


    def _pill_badge(self, text: str, x: float, y: float,
                    color: QColor, is_active: bool = False) -> float:
        font = QFont()
        font.setPointSize(8)
        if is_active:
            font.setBold(True)

        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(text)
        ph = 17          
        pw = tw + 14
        r  = ph / 2

        bg_col = QColor(color)
        bg_col.setAlpha(45 if is_active else 28)

        border_col = QColor(color)
        border_col.setAlpha(180 if is_active else 130)

        path = QPainterPath()
        path.addRoundedRect(x, y - ph / 2, pw, ph, r, r)

        pill = self._scene.addPath(path, QPen(border_col, 1.0), QBrush(bg_col))
        pill.setZValue(3)
        pill.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        txt_col = QColor("#FFFFFF") if is_active else QColor(color)
        t = self._scene.addText(text, font)
        t.setDefaultTextColor(txt_col)
        t.setPos(x + 7, y - ph / 2 + 0.5)
        t.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        t.setZValue(4)

        return x + pw

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
        self._clear_overlays()
        repo = self._state.repo
        if repo is None:
            return

        try:
            head_sha  = repo.head.commit.hexsha
            to_remove = [
                c.hexsha
                for c in repo.iter_commits(f"{target_sha}..{head_sha}")
            ]
        except Exception:
            return

        r          = self.NODE_R + 5
        red_fill   = QColor(255, 69, 58, 50)
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
        for item in self._overlays:
            self._scene.removeItem(item)
        self._overlays.clear()


    def _on_preview_revert(self, target_sha: str):
        """
        Draw a ghost commit node one row above HEAD.
        """
        self._clear_revert_preview()
        repo = self._state.repo
        if repo is None or target_sha not in self._nodes:
            return

        try:
            head_sha = repo.head.commit.hexsha
        except Exception:
            return

        if head_sha not in self._nodes:
            return

        head_pt   = self._nodes[head_sha]
        ghost_pt  = QPointF(head_pt.x(), head_pt.y() - self.ROW_H)
        target_pt = self._nodes[target_sha]
        r         = self.NODE_R

        dash_pen = QPen(QColor(ACCENT_GREEN), 2)
        dash_pen.setStyle(Qt.PenStyle.DashLine)
        ghost_circle = self._scene.addEllipse(
            ghost_pt.x() - r, ghost_pt.y() - r, r * 2, r * 2,
            dash_pen,
            QBrush(QColor(48, 209, 88, 55)),
        )
        ghost_circle.setZValue(8)
        self._revert_ghost.append(ghost_circle)

        mono = QFont()
        mono.setFamilies(["SF Mono", "Menlo", "Consolas"])
        mono.setPointSize(10)
        ghost_lbl = self._scene.addText("new commit  (preview)", mono)
        ghost_lbl.setDefaultTextColor(QColor(ACCENT_GREEN))
        ghost_lbl.setPos(ghost_pt.x() + r + 8, ghost_pt.y() - 9)
        ghost_lbl.setZValue(8)
        self._revert_ghost.append(ghost_lbl)

        solid_pen = QPen(QColor(ACCENT_GREEN), 1.5)
        edge = self._scene.addLine(
            ghost_pt.x(), ghost_pt.y() + r,
            head_pt.x(),  head_pt.y()  - r,
            solid_pen,
        )
        edge.setZValue(7)
        self._revert_ghost.append(edge)

        reverts_pen = QPen(QColor(ACCENT_ORANGE), 1.5)
        reverts_pen.setStyle(Qt.PenStyle.DashLine)
        arrow = self._scene.addLine(
            ghost_pt.x(), ghost_pt.y(),
            target_pt.x(), target_pt.y(),
            reverts_pen,
        )
        arrow.setZValue(7)
        self._revert_ghost.append(arrow)

        ah_pen = QPen(QColor(ACCENT_ORANGE), 1.5)
        dx = target_pt.x() - ghost_pt.x()
        dy = target_pt.y() - ghost_pt.y()
        length = (dx**2 + dy**2) ** 0.5 or 1
        ux, uy = dx / length, dy / length
        px, py = -uy, ux
        tip_x  = target_pt.x() - ux * (r + 2)
        tip_y  = target_pt.y() - uy * (r + 2)
        for sx, sy in [(1, 1), (-1, 1)]:
            ah = self._scene.addLine(
                tip_x, tip_y,
                tip_x - ux*8 + px*5*sx, tip_y - uy*8 + py*5*sy,
                ah_pen,
            )
            ah.setZValue(7)
            self._revert_ghost.append(ah)

        ui_font = QFont(); ui_font.setPointSize(10)
        mid_x = (ghost_pt.x() + target_pt.x()) / 2
        mid_y = (ghost_pt.y() + target_pt.y()) / 2
        rev_lbl = self._scene.addText("reverts", ui_font)
        rev_lbl.setDefaultTextColor(QColor(ACCENT_ORANGE))
        rev_lbl.setPos(mid_x + r + 4, mid_y - 9)
        rev_lbl.setZValue(9)
        self._revert_ghost.append(rev_lbl)

        self.centerOn(ghost_pt)


    def _clear_revert_preview(self):
        """Remove all revert ghost items from the scene."""
        for item in self._revert_ghost:
            self._scene.removeItem(item)
        self._revert_ghost.clear()

    def _on_reflog_entry_selected(self, short_sha: str):
        """Select and centre the node whose SHA starts with short_sha."""
        full_sha = next((s for s in self._nodes if s.startswith(short_sha)), None)
        if full_sha is None:
            return
        self._scene.clearSelection()
        for item in self._scene.items():
            if item.data(0) == full_sha:
                item.setSelected(True)
                break
        self.centerOn(self._nodes[full_sha])


    def _on_selection_changed(self):
        selected = [it for it in self._scene.selectedItems() if it.data(0)]

        if not selected:
            self._selected_sha = None
            self._co_btn.hide()
            self._state.commit_selected.emit(None)
            return

        sha = selected[0].data(0)
        self._selected_sha = sha

        commit = None
        if sha and self._state.repo:
            try:
                commit = self._state.repo.commit(sha)
            except Exception:
                pass

        self._state.commit_selected.emit(commit)

        # Hide checkout button if selected commit is HEAD
        if sha == self._head_sha:
            self._co_btn.hide()
            return

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