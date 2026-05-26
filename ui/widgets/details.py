import os
from datetime import datetime, timezone

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QListWidget, QTextEdit, QPushButton, QListWidgetItem
)
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtCore import Qt, Signal

from git_backend.state import AppState
from utils.helper import label, h_separator
from ui.resources.theme import (
    ACCENT, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED,
    BG_BASE, BG_PANEL, BG_HOVER, SEPARATOR,
    TEXT_SECONDARY, TEXT_TERTIARY, TEXT_PRIMARY,
)
from ui.widgets.diff import DiffPanel


class HeatmapRow(QWidget):
    clicked = Signal(str)  # full filepath

    def __init__(self, path: str, insertions: int, deletions: int, max_churn: int):
        super().__init__()
        self._path  = path
        self._ins   = insertions
        self._del   = deletions
        self._ratio = (insertions + deletions) / max_churn if max_churn > 0 else 0
        self._hov   = False
        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    def _bar_color(self) -> QColor:
        r = self._ratio
        if r < 0.34: return QColor(ACCENT_GREEN)
        if r < 0.67: return QColor(ACCENT_ORANGE)
        return QColor(ACCENT_RED)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        p.fillRect(0, 0, w, h, QColor(BG_HOVER if self._hov else BG_BASE))

        p.setPen(QColor(TEXT_PRIMARY))
        p.setFont(QFont("-apple-system", 11))
        p.drawText(8, 2, w - 68, 16, Qt.AlignLeft | Qt.AlignVCenter,
                   os.path.basename(self._path))

        p.setPen(QColor(TEXT_TERTIARY))
        p.setFont(QFont("-apple-system", 10))
        p.drawText(0, 2, w - 6, 16, Qt.AlignRight | Qt.AlignVCenter,
                   f"+{self._ins} −{self._del}")

        bx, by, bh = 8, h - 9, 5
        bmax = w - 16
        p.setBrush(QColor(SEPARATOR)); p.setPen(Qt.NoPen)
        p.drawRoundedRect(bx, by, bmax, bh, 2, 2)

        p.setBrush(self._bar_color())
        p.drawRoundedRect(bx, by, max(4, int(self._ratio * bmax)), bh, 2, 2)

    def enterEvent(self, _e):   self._hov = True;  self.update()
    def leaveEvent(self, _e):   self._hov = False; self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._path)


class DetailsPanel(QWidget):
    """Shows metadata for the selected commit."""

    def __init__(self, state: AppState):
        super().__init__()
        self._state = state
        self.setObjectName("detailsPanel")
        self.setMinimumWidth(200)
        self.setMaximumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet(f"background: {BG_PANEL};")
        h = QHBoxLayout(header)
        h.setContentsMargins(14, 12, 14, 12)
        h.addWidget(label("Details", 13, TEXT_PRIMARY, 600))
        layout.addWidget(header)
        layout.addWidget(h_separator())

        # ── Scrollable body ─────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        body = QWidget()
        body.setStyleSheet(f"background: {BG_PANEL};")
        vbox = QVBoxLayout(body)
        vbox.setContentsMargins(14, 10, 14, 10)
        vbox.setSpacing(6)

        # SHA
        vbox.addWidget(label("Commit", 11, TEXT_TERTIARY, 600))
        self._sha_lbl = label("—", 13, ACCENT)
        self._sha_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        vbox.addWidget(self._sha_lbl)

        vbox.addSpacing(8)
        vbox.addWidget(h_separator())

        # Author / Date / Branch
        self._meta_labels: dict[str, QLabel] = {}
        for key in ("Author", "Date", "Branch"):
            row = QHBoxLayout()
            row.addWidget(label(key, 12, TEXT_TERTIARY))
            row.addStretch()
            val = label("—", 12, TEXT_PRIMARY)
            self._meta_labels[key] = val
            row.addWidget(val)
            vbox.addLayout(row)

        vbox.addSpacing(8)
        vbox.addWidget(h_separator())

        # Commit message
        vbox.addWidget(label("Message", 11, TEXT_TERTIARY, 600))
        self._msg_edit = QTextEdit()
        self._msg_edit.setReadOnly(True)
        self._msg_edit.setFixedHeight(70)
        self._msg_edit.setStyleSheet(
            f"color: {TEXT_PRIMARY}; border: 1px solid {TEXT_TERTIARY};"
        )
        vbox.addWidget(self._msg_edit)

        vbox.addSpacing(8)
        vbox.addWidget(h_separator())

        # Parents
        vbox.addWidget(label("Parents", 11, TEXT_TERTIARY, 600))
        parents_row = QWidget()
        self._parents_layout = QHBoxLayout(parents_row)
        self._parents_layout.setContentsMargins(0, 0, 0, 0)
        self._parents_layout.setSpacing(6)
        self._parents_layout.setAlignment(Qt.AlignLeft)
        vbox.addWidget(parents_row)

        vbox.addSpacing(8)
        vbox.addWidget(h_separator())

        # Changed-files header with count badge
        fh = QHBoxLayout()
        fh.addWidget(label("Changed Files", 11, TEXT_TERTIARY, 600))
        fh.addStretch()
        self._file_count_lbl = label("", 10, TEXT_TERTIARY)
        fh.addWidget(self._file_count_lbl)
        vbox.addLayout(fh)

        # Placeholder shown when no commit is selected
        self._no_commit_lbl = label("Select a commit to inspect", 12, TEXT_TERTIARY)
        vbox.addWidget(self._no_commit_lbl)

        # Heatmap rows are injected here
        self._heatmap_widget = QWidget()
        self._heatmap_widget.setStyleSheet(f"background: {BG_PANEL};")
        self._heatmap_vbox = QVBoxLayout(self._heatmap_widget)
        self._heatmap_vbox.setContentsMargins(0, 2, 0, 4)
        self._heatmap_vbox.setSpacing(0)
        vbox.addWidget(self._heatmap_widget)

        vbox.addStretch()

        scroll.setWidget(body)
        layout.addWidget(scroll)

        # ── State connections ────────────────────────────────────────────────
        state.repo_changed.connect(self._on_repo_changed)
        state.commit_selected.connect(self._on_commit_selected)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _clear_parents(self):
        """Remove all parent-SHA buttons."""
        while self._parents_layout.count():
            item = self._parents_layout.takeAt(0)
            if w := item.widget():
                w.deleteLater()

    def _clear_heatmap(self):
        """Remove all heatmap rows."""
        while self._heatmap_vbox.count():
            item = self._heatmap_vbox.takeAt(0)
            if w := item.widget():
                w.deleteLater()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_repo_changed(self, _repo):
        self._on_commit_selected(None)

    def _on_commit_selected(self, commit):
        if commit is None:
            self._sha_lbl.setText("—")
            for v in self._meta_labels.values():
                v.setText("—")
            self._msg_edit.clear()
            self._file_count_lbl.setText("")
            self._no_commit_lbl.setVisible(True)
            self._clear_parents()
            self._clear_heatmap()
            return

        # SHA
        self._sha_lbl.setText(commit.hexsha[:12])
        self._sha_lbl.setToolTip(commit.hexsha)

        # Author / Date / Branch
        self._meta_labels["Author"].setText(str(commit.author.name)[:22])
        dt = datetime.fromtimestamp(commit.authored_date, tz=timezone.utc)
        self._meta_labels["Date"].setText(dt.strftime("%Y-%m-%d %H:%M"))
        self._meta_labels["Branch"].setText(self._state.active_branch or "—")

        # Message
        self._msg_edit.setPlainText(commit.message.strip())

        # Parents
        self._clear_parents()
        for parent in commit.parents:
            btn = QPushButton(parent.hexsha[:12])
            btn.setFlat(True)
            btn.setStyleSheet(
                f"color: {ACCENT}; font-family: monospace; border: none; padding: 0;"
            )
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda checked=False, p=parent.hexsha:
                    self._state.commit_selected.emit(
                        self._state.repo.commit(p) if self._state.repo else None
                    )
            )
            self._parents_layout.addWidget(btn)

        self._no_commit_lbl.setVisible(False)
        self._populate_heatmap(commit)

    def _populate_heatmap(self, commit):
        self._clear_heatmap()
        try:
            stats = commit.stats.files
        except Exception:
            return
        if not stats:
            return

        max_churn = max(v["insertions"] + v["deletions"] for v in stats.values()) or 1
        n = len(stats)
        self._file_count_lbl.setText(f"{n} file{'s' if n != 1 else ''}")

        # Group files by directory
        dirs: dict[str, list] = {}
        for path, data in stats.items():
            dirs.setdefault(os.path.dirname(path) or ".", []).append((path, data))

        for dir_name in sorted(dirs):
            dl = label(dir_name + "/", 10, TEXT_TERTIARY, 500)
            dl.setContentsMargins(6, 8, 6, 2)
            self._heatmap_vbox.addWidget(dl)
            for path, data in sorted(
                dirs[dir_name],
                key=lambda x: -(x[1]["insertions"] + x[1]["deletions"]),
            ):
                row = HeatmapRow(
                    path,
                    data.get("insertions", 0),
                    data.get("deletions", 0),
                    max_churn,
                )
                row.clicked.connect(lambda p, c=commit: self._open_diff(c, p))
                self._heatmap_vbox.addWidget(row)

        self._heatmap_vbox.addStretch()

    def _open_diff(self, commit, filepath: str):
        DiffPanel(self._state, commit, filepath, parent=self.window()).show()