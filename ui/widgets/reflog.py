from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTreeWidget, QTreeWidgetItem, QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui  import QFont, QColor

from ui.resources.theme     import (
    BG_BASE, BG_PANEL, BG_HOVER, SEPARATOR,
    ACCENT, ACCENT_GREEN, ACCENT_RED, ACCENT_ORANGE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
)
from utils.helper import label

_ACTION_COLOR = {
    "commit":   ACCENT_GREEN,
    "checkout": ACCENT,
    "switch":   ACCENT,
    "reset":    ACCENT_ORANGE,
    "merge":    ACCENT,
    "revert":   ACCENT_RED,
    "pull":     ACCENT,
    "push":     ACCENT,
}

_COL_IDX = 0
_COL_ACT = 1
_COL_SHA = 2
_COL_MSG = 3


class ReflogTab(QWidget):
    def __init__(self, state):
        super().__init__()
        self._state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Educational banner ────────────────────────────────────────────────
        banner = QWidget()
        banner.setStyleSheet(
            f"background:{BG_PANEL}; border-bottom:1px solid {SEPARATOR};"
        )
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(16, 10, 16, 10)
        bl.setSpacing(10)

        note = QLabel(
            "◈  The reflog records every position HEAD has visited including after "
            "resets and branch deletions. Commits listed here are still recoverable "
            "even if no branch points to them. Click any entry to jump to it on the DAG."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            f"color:{TEXT_SECONDARY}; font-size:12px; background:transparent;"
        )
        bl.addWidget(note, 1)

        self._count_lbl = label("— entries", 11, TEXT_TERTIARY)
        self._refresh_btn = QPushButton("↺  Refresh")
        self._refresh_btn.setStyleSheet(
            f"background:{BG_HOVER}; border:none; border-radius:5px;"
            f"color:{TEXT_PRIMARY}; font-size:12px; padding:4px 10px;"
        )
        self._refresh_btn.clicked.connect(self._load)
        bl.addWidget(self._count_lbl)
        bl.addWidget(self._refresh_btn)
        root.addWidget(banner)

        # ── Tree ──────────────────────────────────────────────────────────────
        self._tree = QTreeWidget()
        self._tree.setObjectName("reflogTree")
        self._tree.setHeaderLabels(["#", "Action", "SHA", "Message"])
        self._tree.setRootIsDecorated(False)
        self._tree.setIndentation(0)
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)

        hdr = self._tree.header()
        hdr.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        hdr.resizeSection(_COL_IDX, 42)
        hdr.resizeSection(_COL_ACT, 90)
        hdr.resizeSection(_COL_SHA, 74)
        hdr.setStretchLastSection(True)
        hdr.setStyleSheet(
            f"QHeaderView::section {{"
            f"  background:{BG_PANEL}; color:{TEXT_TERTIARY}; font-size:11px;"
            f"  font-weight:600; padding:4px 8px; border:none;"
            f"  border-bottom:1px solid {SEPARATOR};"
            f"}}"
        )

        self._tree.itemClicked.connect(self._on_item_clicked)
        root.addWidget(self._tree)

        state.repo_changed.connect(self._on_repo_changed)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_repo_changed(self, repo):
        self._tree.clear()
        self._count_lbl.setText("— entries")
        if repo is not None:
            self._load()

    def _load(self):
        repo = self._state.repo
        if repo is None:
            return
        self._tree.clear()
        try:
            raw = repo.git.reflog()
        except Exception:
            return

        entries = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                left, rest = line.split(": ", 1)
                tokens     = left.split()
                sha        = tokens[0]
                ref        = tokens[1]                          # HEAD@{N}
                idx        = ref[ref.index("{") + 1 : ref.index("}")]
                parts      = rest.split(": ", 1)
                action     = parts[0]
                message    = parts[1] if len(parts) > 1 else rest
            except (ValueError, IndexError):
                continue
            entries.append((idx, action, sha, message))

        _mono = QFont()
        _mono.setFamilies(["SF Mono", "Menlo", "Consolas"])
        _mono.setPointSize(11)

        for idx, action, sha, message in entries:
            it    = QTreeWidgetItem([idx, action, sha, message])
            color = _ACTION_COLOR.get(action.split()[0].lower(), TEXT_SECONDARY)
            it.setForeground(_COL_IDX, QColor(TEXT_TERTIARY))
            it.setForeground(_COL_ACT, QColor(color))
            it.setForeground(_COL_SHA, QColor(ACCENT))
            it.setForeground(_COL_MSG, QColor(TEXT_SECONDARY))
            it.setFont(_COL_SHA, _mono)
            it.setData(_COL_SHA, Qt.ItemDataRole.UserRole, sha)
            self._tree.addTopLevelItem(it)

        n = len(entries)
        self._count_lbl.setText(f"{n} {'entry' if n == 1 else 'entries'}")

    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int):
        sha = item.data(_COL_SHA, Qt.ItemDataRole.UserRole)
        if sha:
            self._state.reflog_entry_selected.emit(sha)