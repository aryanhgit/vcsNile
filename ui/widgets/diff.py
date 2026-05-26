import difflib
import os

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QPlainTextEdit, QTextEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui  import QFont, QColor, QTextCursor, QTextCharFormat

from ui.resources.theme     import (
    BG_BASE, BG_PANEL, SEPARATOR,
    ACCENT, ACCENT_GREEN, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
)
from utils.helper import label, dot_badge

_MAX_LINES = 3000


def _build_side_by_side(old_text: str, new_text: str):
    """Return (old_rows, new_rows), each list of (line_no_str, text, highlighted)."""
    old_lines = old_text.splitlines()[:_MAX_LINES] if old_text else []
    new_lines = new_text.splitlines()[:_MAX_LINES] if new_text else []

    matcher  = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    old_rows: list = []
    new_rows: list = []
    old_no, new_no = 1, 1

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                old_rows.append((str(old_no + k), old_lines[i1 + k], False))
                new_rows.append((str(new_no + k), new_lines[j1 + k], False))
            old_no += i2 - i1
            new_no += j2 - j1
        elif tag == "replace":
            n_old, n_new = i2 - i1, j2 - j1
            for k in range(max(n_old, n_new)):
                old_rows.append((str(old_no + k), old_lines[i1 + k], True)  if k < n_old else ("", "", False))
                new_rows.append((str(new_no + k), new_lines[j1 + k], True)  if k < n_new else ("", "", False))
            old_no += n_old
            new_no += n_new
        elif tag == "delete":
            for k in range(i2 - i1):
                old_rows.append((str(old_no + k), old_lines[i1 + k], True))
                new_rows.append(("", "", False))
            old_no += i2 - i1
        elif tag == "insert":
            for k in range(j2 - j1):
                old_rows.append(("", "", False))
                new_rows.append((str(new_no + k), new_lines[j1 + k], True))
            new_no += j2 - j1

    return old_rows, new_rows


class DiffPanel(QDialog):
    def __init__(self, state, commit, filepath: str, parent=None):
        super().__init__(parent)
        self._state   = state
        self._syncing = False

        self.setWindowTitle(f"Diff — {os.path.basename(filepath)}")
        self.resize(1100, 660)
        self.setMinimumSize(820, 420)
        self.setModal(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setStyleSheet(f"background:{BG_PANEL}; border-bottom:1px solid {SEPARATOR};")
        hl  = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 10, 16, 10)
        hl.addWidget(label(f"⬡  {filepath}", 13, TEXT_PRIMARY, 500))
        hl.addStretch()
        hl.addWidget(label(f"◇ {commit.hexsha[:7]}", 12, ACCENT))
        root.addWidget(hdr)

        # ── Two-column diff ───────────────────────────────────────────────────
        old_text, new_text = self._get_texts(commit, filepath)
        old_rows, new_rows = _build_side_by_side(old_text, new_text)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        self._old_editor = self._make_pane(splitter, "Before", old_rows, ACCENT_RED)
        self._new_editor = self._make_pane(splitter, "After",  new_rows, ACCENT_GREEN)
        splitter.setSizes([550, 550])
        root.addWidget(splitter)

        # ── Sync scrollbars ───────────────────────────────────────────────────
        ob = self._old_editor.verticalScrollBar()
        nb = self._new_editor.verticalScrollBar()
        ob.valueChanged.connect(lambda v: self._sync(nb, v))
        nb.valueChanged.connect(lambda v: self._sync(ob, v))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _sync(self, bar, value: int):
        if not self._syncing:
            self._syncing = True
            bar.setValue(value)
            self._syncing = False

    def _get_texts(self, commit, filepath: str):
        repo = self._state.repo
        # Handle renames: "old/path → new/path"
        if " → " in filepath:
            old_fp, new_fp = [p.strip() for p in filepath.split(" → ", 1)]
        else:
            old_fp = new_fp = filepath

        def _show(sha: str, path: str) -> str:
            try:
                text = repo.git.show(f"{sha}:{path}")
                return "" if "\x00" in text else text   # skip binary
            except Exception:
                return ""

        new_text = _show(commit.hexsha, new_fp)
        old_text = _show(commit.parents[0].hexsha, old_fp) if commit.parents else ""
        return old_text, new_text

    def _make_pane(self, splitter: QSplitter, title: str,
                   rows: list, accent: str) -> QPlainTextEdit:
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Pane header
        ph  = QWidget()
        ph.setStyleSheet(f"background:{BG_PANEL}; border-bottom:1px solid {SEPARATOR};")
        phl = QHBoxLayout(ph)
        phl.setContentsMargins(12, 6, 12, 6)
        phl.addWidget(dot_badge(accent))
        phl.addSpacing(6)
        phl.addWidget(label(title, 12, TEXT_PRIMARY, 500))
        phl.addStretch()
        n_hl = sum(1 for _, _, h in rows if h)
        phl.addWidget(label(f"{n_hl} line{'s' if n_hl != 1 else ''}", 11, TEXT_TERTIARY))
        lay.addWidget(ph)

        # Editor
        editor = QPlainTextEdit()
        editor.setObjectName("diffEditor")
        editor.setReadOnly(True)
        editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        f = QFont()
        f.setFamilies(["SF Mono", "Menlo", "Consolas"])
        f.setPointSize(11)
        editor.setFont(f)

        # Build plain text (line-number gutter via prefix)
        lines: list[str] = []
        hl_indices: list[int] = []
        for i, (ln, text, hl) in enumerate(rows):
            lines.append((f"{ln:>4} │ " if ln else "     │ ") + text)
            if hl:
                hl_indices.append(i)
        editor.setPlainText("\n".join(lines))

        # Line-level highlights via ExtraSelections
        hl_bg = QColor(accent)
        hl_bg.setAlpha(52)
        hl_fg = QColor(accent).lighter(155)
        sels: list = []
        doc = editor.document()
        for idx in hl_indices:
            block = doc.findBlockByLineNumber(idx)
            if not block.isValid():
                continue
            cur = QTextCursor(block)
            cur.select(QTextCursor.LineUnderCursor)
            fmt = QTextCharFormat()
            fmt.setBackground(hl_bg)
            fmt.setForeground(hl_fg)
            sel = QTextEdit.ExtraSelection()
            sel.cursor = cur
            sel.format  = fmt
            sels.append(sel)
        editor.setExtraSelections(sels)

        lay.addWidget(editor)
        splitter.addWidget(w)
        return editor