import os

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QFont, QColor, QBrush,
    QTextCursor, QTextCharFormat,
)
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QComboBox, QDialog, QSplitter
)
from PySide6.QtGui import QIcon

from ui.resources.theme import STYLESHEET
from ui.resources.constants import (ACCENT, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED, BG_BASE, 
                                    BG_PANEL, SEPARATOR, TEXT_PRIMARY, TEXT_TERTIARY, TEXT_SECONDARY)
from utils.helper import label, h_separator, dot_badge
from utils.state import AppState

class ConflictParser:
    """
    Parses a file that contains Git conflict markers into typed line regions.
    Supports both standard and diff3 formats.
    """

    @staticmethod
    def parse(text: str) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        state  = "context"
        for line in text.splitlines(keepends=True):
            s = line.rstrip("\r\n")
            if   s.startswith("<<<<<<<"):   state = "ours";     result.append(("marker", line))
            elif s.startswith("|||||||"):   state = "ancestor"; result.append(("marker", line))
            elif s.startswith("======="):   state = "theirs";   result.append(("marker", line))
            elif s.startswith(">>>>>>>"):   state = "context";  result.append(("marker", line))
            else:                                                result.append((state,    line))
        return result

    @staticmethod
    def ours_text(regions: list) -> str:
        return "".join(l for k, l in regions if k == "ours")

    @staticmethod
    def theirs_text(regions: list) -> str:
        return "".join(l for k, l in regions if k == "theirs")

    @staticmethod
    def ancestor_text(regions: list) -> str:
        return "".join(l for k, l in regions if k == "ancestor")

    @staticmethod
    def conflict_count(regions: list) -> int:
        """Number of distinct conflict blocks (count of <<<<<<< markers)."""
        return sum(1 for k, l in regions
                   if k == "marker" and l.lstrip().startswith("<<<<<<<"))

class ConflictPane(QWidget):
    """
    One panel in the three-panel merge conflict view.
    """

    _BG: dict[str, tuple] = {
        "ours":     (10,  132, 255, 45),
        "theirs":   (255, 159,  10, 45),
        "ancestor": (120, 120, 128, 30),
        "marker":   (255,  69,  58, 70),
    }

    def __init__(self, title: str, subtitle: str, accent: str):
        super().__init__()
        self.setObjectName("conflictPane")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setStyleSheet(f"background:{BG_PANEL};")
        hl  = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 10, 12, 10)
        hl.setSpacing(8)
        hl.addWidget(dot_badge(accent, 8))
        hl.addWidget(label(title, 13, TEXT_PRIMARY, 600))
        hl.addStretch()
        self._line_count = label("", 10, TEXT_TERTIARY)
        hl.addWidget(self._line_count)
        root.addWidget(hdr)
        root.addWidget(h_separator())

        sub = label(f"  {subtitle}", 11, TEXT_TERTIARY)
        sub.setContentsMargins(12, 3, 0, 3)
        root.addWidget(sub)
        root.addWidget(h_separator())

        # Editor
        self._editor = QPlainTextEdit()
        self._editor.setObjectName("conflictEditor")
        self._editor.setReadOnly(True)
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        mono = QFont()
        mono.setFamilies(["SF Mono", "Menlo", "Consolas"])
        mono.setPointSize(11)
        self._editor.setFont(mono)
        root.addWidget(self._editor)


    def set_plain(self, text: str):
        """Populate with plain text."""
        self._editor.setPlainText(text)
        n = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        self._line_count.setText(f"{n} lines")


    def set_regions(self, regions: list[tuple[str, str]]):
        """
        Populate with coloured regions from ConflictParser.parse().
        Each region: (kind, newline).
        """
        self._editor.clear()
        cursor = QTextCursor(self._editor.document())

        for kind, line in regions:
            fmt = QTextCharFormat()
            rgba = self._BG.get(kind)
            if rgba:
                fmt.setBackground(QBrush(QColor(*rgba)))
            if kind == "marker":
                fmt.setFontWeight(700)
                fmt.setForeground(QBrush(QColor(ACCENT_RED)))
            cursor.insertText(line, fmt)

        self._line_count.setText(f"{len(regions)} lines")

class MergeConflictVisualizer(QDialog):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state

        self.setWindowTitle("Merge Conflict Visualizer")
        self.setModal(False)
        self.resize(1120, 700)
        self.setMinimumSize(820, 520)
        self.setStyleSheet(STYLESHEET)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        bar = QWidget()
        bar.setStyleSheet(f"background:{BG_PANEL};")
        bl  = QHBoxLayout(bar)
        bl.setContentsMargins(14, 10, 14, 10)
        bl.setSpacing(10)

        icon_label = QLabel()
        icon_label.setStyleSheet("background: transparent; border: none;")
        icon_pixmap = QIcon("ui/resources/assets/merge_icon.svg").pixmap(18, 18)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedSize(18, 18)

        bl.addWidget(icon_label)
        bl.addWidget(label("Merge Conflict Visualizer", 14, TEXT_PRIMARY, 700))
        bl.addStretch()
        bl.addWidget(label("File:", 12, TEXT_SECONDARY))

        self._file_combo = QComboBox()
        self._file_combo.setObjectName("ttCombo")
        self._file_combo.setMinimumWidth(280)
        self._file_combo.currentIndexChanged.connect(self._load_file)
        bl.addWidget(self._file_combo)

        scan_btn = QPushButton("↺  Scan")
        scan_btn.setObjectName("rvPreviewBtn")
        scan_btn.setFixedHeight(28)
        scan_btn.clicked.connect(self._scan)
        bl.addWidget(scan_btn)
        root.addWidget(bar)
        root.addWidget(h_separator())

        leg = QWidget()
        leg.setStyleSheet(f"background:{BG_PANEL};")
        ll  = QHBoxLayout(leg)
        ll.setContentsMargins(14, 5, 14, 5)
        ll.setSpacing(18)
        ll.addWidget(label("Legend:", 11, TEXT_TERTIARY))
        for lbl, color in [
            ("Ours (current)",   ACCENT),
            ("Theirs (incoming)", ACCENT_ORANGE),
            ("Ancestor",          TEXT_TERTIARY),
            ("Conflict marker",   ACCENT_RED),
        ]:
            r = QHBoxLayout(); r.setSpacing(5)
            r.addWidget(dot_badge(color, 8))
            r.addWidget(label(lbl, 10, TEXT_SECONDARY))
            ll.addLayout(r)
        ll.addStretch()
        root.addWidget(leg)
        root.addWidget(h_separator())

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setHandleWidth(1)

        self._base_pane   = ConflictPane(
            "Common Ancestor", "base — shared origin",   TEXT_TERTIARY)
        self._result_pane = ConflictPane(
            "Conflicted Result", "file on disk — coloured by region", ACCENT)
        self._theirs_pane = ConflictPane(
            "Incoming Changes", "MERGE_HEAD / theirs",   ACCENT_ORANGE)

        split.addWidget(self._base_pane)
        split.addWidget(self._result_pane)
        split.addWidget(self._theirs_pane)
        split.setSizes([280, 420, 280])
        root.addWidget(split)

        root.addWidget(h_separator())
        self._status = label("", 11, TEXT_TERTIARY)
        self._status.setContentsMargins(14, 4, 14, 4)
        root.addWidget(self._status)

        state.repo_changed.connect(self._on_repo_changed)

    def showEvent(self, event):
        super().showEvent(event)
        self._scan()


    def _on_repo_changed(self, _repo):
        self._file_combo.clear()
        self._base_pane.set_plain("")
        self._result_pane.set_regions([])
        self._theirs_pane.set_plain("")
        self._status.setText("")


    def _scan(self):
        repo = self._state.repo
        if repo is None:
            self._status.setText("No repository loaded.")
            return

        self._file_combo.clear()
        paths: list[str] = []

        try:
            unmerged = repo.index.unmerged_blobs()
            paths = sorted(unmerged.keys())
        except Exception:
            pass

        if not paths:
            try:
                out = repo.git.diff("--name-only", "--diff-filter=U")
                paths = [p.strip() for p in out.splitlines() if p.strip()]
            except Exception:
                pass

        for p in paths:
            self._file_combo.addItem(p, userData=p)

        if paths:
            self._status.setText(
                f"Found {len(paths)} conflicted file(s). Select one above."
            )
        else:
            self._status.setText(
                "No conflicts detected repository may not be in a merge state."
            )
            self._state.logger.log("Conflict scan: no conflicts found")


    def _load_file(self):
        repo = self._state.repo
        if repo is None or self._file_combo.count() == 0:
            return
        path = self._file_combo.currentData()
        if not path:
            return

        full = os.path.join(repo.working_dir, path)

        try:
            raw     = open(full, "r", errors="replace").read()
            regions = ConflictParser.parse(raw)
        except Exception as exc:
            self._result_pane.set_plain(f"Error reading {path}: {exc}")
            return
        self._result_pane.set_regions(regions)

        base = self._get_stage(repo, path, stage=1)

        if not base:
            base = ConflictParser.ancestor_text(regions)

        if not base:
            try:
                bases = repo.merge_base("HEAD", "MERGE_HEAD")
                if bases:
                    base = bases[0].tree[path].data_stream.read().decode(
                        "utf-8", errors="replace"
                    )
            except Exception:
                pass

        self._base_pane.set_plain(base or "(ancestor not available)")

        theirs = self._get_stage(repo, path, stage=3)

        if not theirs:
            theirs = ConflictParser.theirs_text(regions)

        if not theirs:
            try:
                theirs = repo.git.show(f"MERGE_HEAD:{path}")
            except Exception:
                pass

        self._theirs_pane.set_plain(theirs or "(incoming not available)")

        n_conflicts = ConflictParser.conflict_count(regions)
        self._status.setText(
            f"{path}  ·  {n_conflicts} conflict block(s)  ·  "
            f"{len(regions)} lines total"
        )
        self._state.logger.log(
            f"Conflict view: {path}  ({n_conflicts} block(s))"
        )


    @staticmethod
    def _get_stage(repo, path: str, stage: int) -> str:
        """
        Read file content from the git index at the given stage.
        """
        try:
            unmerged = repo.index.unmerged_blobs()
            if path in unmerged:
                blobs = {s: b for s, b in unmerged[path]}
                if stage in blobs:
                    return blobs[stage].data_stream.read().decode(
                        "utf-8", errors="replace"
                    )
        except Exception:
            pass
        return ""