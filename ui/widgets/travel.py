from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QFont, QColor, QAction, QKeySequence,
    QPainter, QPen, QBrush,               # ← add (required by StagingDiagram)
)
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPlainTextEdit, QLineEdit, QFrame, QPushButton, QSizePolicy, QScrollArea, 
    QRadioButton, QCheckBox, QButtonGroup, QComboBox, QDialog,
)

from ui.resources.theme import STYLESHEET
from ui.resources.constants import (ACCENT, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED, BG_BASE, 
                                    BG_PANEL, SEPARATOR, TEXT_PRIMARY, TEXT_TERTIARY, TEXT_SECONDARY)
from utils.helper import label, h_separator
from utils.state import AppState


class _ResetDagPreview(QWidget):
    """
    Mini commit strip for the reset preview dialog.

    Each row shows one commit with a coloured status badge:
      ✗  removed  — commits that will disappear from the branch  (red)
      ◎  new HEAD — commit the branch pointer will move to       (orange)

    Removed commits use QFont.setStrikeOut to reinforce the "gone" concept.
    At most 6 removed commits are shown; excess collapses to "… N more".
    """

    def __init__(self):
        super().__init__()
        self.setObjectName("resetDagPreview")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(4)
        self._body = lay

    # ── Public ────────────────────────────────────────────────────────────────

    def set_data(self, removed: list, target_sha: str, target_msg: str):
        """
        removed   : list of (full_sha, first_line_of_message) tuples (HEAD → target).
        target_sha: SHA of the commit HEAD will land on.
        target_msg: first line of that commit's message.
        """
        self._clear()

        if not removed:
            self._add_row("", "(HEAD is already at the target — nothing removed)", "info")
        else:
            for sha, msg in removed[:6]:
                self._add_row(sha, msg, "removed")
            if len(removed) > 6:
                self._add_row("", f"… and {len(removed) - 6} more commit(s)", "info")

        self._add_row(target_sha, target_msg, "target")

    # ── Private ───────────────────────────────────────────────────────────────

    _ROW_META = {
        "removed": ("✗", ACCENT_RED,    "removed",   True),   # (dot, color, badge, strikethrough)
        "target":  ("◎", ACCENT_ORANGE, "new HEAD",  False),
        "info":    ("·", TEXT_TERTIARY, "",           False),
    }

    def _add_row(self, sha: str, msg: str, kind: str):
        dot_glyph, color, badge_label, strike = self._ROW_META[kind]

        row = QWidget()
        row.setStyleSheet("background:transparent;")
        rl  = QHBoxLayout(row)
        rl.setContentsMargins(4, 1, 4, 1)
        rl.setSpacing(8)

        # Leading dot
        rl.addWidget(label(dot_glyph, 12, color, 700))

        # SHA (monospaced, fixed width)
        if sha:
            sha_lbl = QLabel(sha[:7])
            sha_lbl.setFixedWidth(50)
            f = QFont(); f.setFamilies(["SF Mono", "Menlo", "Consolas"]); f.setPointSize(10)
            sha_lbl.setFont(f)
            sha_lbl.setStyleSheet(f"color:{TEXT_SECONDARY}; background:transparent;")
            rl.addWidget(sha_lbl)

        # Commit message — strikethrough for removed commits
        msg_lbl = QLabel(msg[:52])
        mf = QFont(); mf.setPointSize(12); mf.setStrikeOut(strike)
        msg_lbl.setFont(mf)
        msg_lbl.setStyleSheet(
            f"color:{'rgba(255,69,58,0.65)' if kind == 'removed' else TEXT_TERTIARY};"
            " background:transparent;"
        )
        rl.addWidget(msg_lbl)

        # Status badge pill
        if badge_label:
            badge = QLabel(f" {badge_label} ")
            badge.setStyleSheet(
                f"color:white; background:{color}; border-radius:3px;"
                " font-size:10px; font-weight:600; padding:0 4px;"
            )
            rl.addWidget(badge)

        rl.addStretch()
        self._body.addWidget(row)

    def _clear(self):
        while self._body.count():
            item = self._body.takeAt(0)
            if item.widget():
                item.widget().deleteLater()



class _ModeStateDiagram(QWidget):
    """
    Before → After diagram for each reset mode.

    Three layers always shown:
        Working Directory  |  Index / Staging  |  Commit History

    Calling set_mode(0|1|2) updates status badges and tooltip text in-place
    without rebuilding the widget tree.

    Visual key:
        Green  ✓  — layer is preserved / unchanged
        Orange ⚠  — layer is modified  (unstaged / moved)
        Red    ✗  — layer is discarded (hard mode only)
    """

    _ROWS = ["Working Dir", "Index / Staging", "Commit History"]

    # (status_text, badge_color, explanation)
    _EFFECTS: dict[int, list] = {
        0: [  # --soft
            ("✓ Unchanged",     ACCENT_GREEN,  "Files on disk are untouched."),
            ("✓ Stays staged",  ACCENT_GREEN,  "Removed commits' changes land staged — re-commit immediately."),
            ("⟵ Moved back",   ACCENT_ORANGE, "Branch pointer walks back to the target commit."),
        ],
        1: [  # --mixed  (default)
            ("✓ Unchanged",     ACCENT_GREEN,  "Files on disk are untouched."),
            ("⚠ Unstaged",      ACCENT_ORANGE, "Changes are present but unstaged — re-add before committing."),
            ("⟵ Moved back",   ACCENT_ORANGE, "Branch pointer walks back to the target commit."),
        ],
        2: [  # --hard
            ("✗ Discarded",     ACCENT_RED,    "All local changes to tracked files are permanently deleted."),
            ("✗ Discarded",     ACCENT_RED,    "Staged changes are permanently deleted. No recovery path."),
            ("⟵ Moved back",   ACCENT_ORANGE, "Branch pointer walks back to the target commit."),
        ],
    }

    def __init__(self):
        super().__init__()
        self.setObjectName("resetDiagram")

        grid = QVBoxLayout(self)
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setSpacing(6)

        # Column header
        header = QHBoxLayout()
        header.setSpacing(0)
        header.addWidget(label("Layer", 10, TEXT_TERTIARY, 600), stretch=2)
        header.addWidget(label("Before",  10, TEXT_TERTIARY, 600), stretch=2)
        header.addWidget(label("",        10, TEXT_TERTIARY),      stretch=1)   # arrow col
        header.addWidget(label("After",   10, TEXT_TERTIARY, 600), stretch=2)
        header.addWidget(label("",        10, TEXT_TERTIARY),      stretch=3)   # explanation
        grid.addLayout(header)
        grid.addWidget(h_separator())

        # Three data rows — store refs for in-place updates
        self._badges: list[QLabel] = []
        self._arrows: list[QLabel] = []
        self._tips:   list[QLabel] = []

        for row_name, (status, color, tip) in zip(self._ROWS, self._EFFECTS[1]):
            row = QHBoxLayout()
            row.setSpacing(6)

            # Layer name
            row.addWidget(label(row_name, 12, TEXT_SECONDARY, 500), stretch=2)

            # "Before" static pill
            before = QLabel("existing")
            before.setAlignment(Qt.AlignCenter)
            before.setStyleSheet(
                f"color:{TEXT_TERTIARY}; background:{BG_PANEL}; border-radius:4px;"
                " font-size:11px; padding:3px 6px;"
            )
            row.addWidget(before, stretch=2)

            # Arrow (colour updates with mode)
            arrow = label("→", 14, color, 700)
            arrow.setAlignment(Qt.AlignCenter)
            self._arrows.append(arrow)
            row.addWidget(arrow, stretch=1)

            # "After" status badge (updates with mode)
            badge = QLabel(status)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(
                f"color:white; background:{color}; border-radius:4px;"
                " font-size:11px; font-weight:600; padding:3px 6px;"
            )
            self._badges.append(badge)
            row.addWidget(badge, stretch=2)

            # Explanation (updates with mode)
            tip_lbl = label(tip, 10, TEXT_TERTIARY)
            tip_lbl.setWordWrap(True)
            self._tips.append(tip_lbl)
            row.addWidget(tip_lbl, stretch=3)

            grid.addLayout(row)

    def set_mode(self, mode: int):
        """Update all three rows to reflect the chosen mode."""
        for i, (status, color, tip) in enumerate(self._EFFECTS[mode]):
            self._badges[i].setText(status)
            self._badges[i].setStyleSheet(
                f"color:white; background:{color}; border-radius:4px;"
                " font-size:11px; font-weight:600; padding:3px 6px;"
            )
            self._arrows[i].setStyleSheet(
                f"color:{color}; font-size:14px; font-weight:700; background:transparent;"
            )
            self._tips[i].setText(tip)



# ─────────────────────────────────────────────────────────────────────────────
# Reset Visualizer
# ─────────────────────────────────────────────────────────────────────────────

class StagingDiagram(QWidget):
    """
    Custom-painted before/after diagram showing what each reset mode does
    to the three git areas: Working Dir | Index / Stage | Repository.

    Layout: two rows (BEFORE / AFTER) × three columns.
    Each cell is a colour-coded rounded rectangle with a status label.
    Repaints automatically when set_mode() is called — no child widgets.

    Mode effects on the removed commits' changes
    ─────────────────────────────────────────────
    soft  — WD: unchanged   Index: diffs STAGED   Repo: HEAD ← target
    mixed — WD: diffs kept  Index: CLEARED        Repo: HEAD ← target
    hard  — WD: OVERWRITTEN Index: CLEARED        Repo: HEAD ← target
    """

    _COLS = ["Working Dir", "Index / Stage", "Repository"]

    # Constant BEFORE row: (label, hex_color, fill_alpha)
    _BEFORE: list[tuple[str, str, int]] = [
        ("files as-is",         ACCENT_GREEN,  30),
        ("clean",               TEXT_TERTIARY, 20),
        ("A ← B ← C  HEAD=C",  ACCENT,        25),
    ]

    # AFTER row by mode: [(label, hex_color, fill_alpha), ...]
    _AFTER: dict[str, list[tuple[str, str, int]]] = {
        "soft": [
            ("unchanged",           ACCENT_GREEN,  30),
            ("diffs STAGED  ←",     ACCENT_ORANGE, 50),
            ("A  (HEAD=A)",         ACCENT,        25),
        ],
        "mixed": [
            ("diffs unstaged",      ACCENT_GREEN,  35),
            ("cleared",             ACCENT_RED,    50),
            ("A  (HEAD=A)",         ACCENT,        25),
        ],
        "hard": [
            ("OVERWRITTEN  ⚠",     ACCENT_RED,    60),
            ("cleared",             ACCENT_RED,    50),
            ("A  (HEAD=A)",         ACCENT,        25),
        ],
    }

    def __init__(self):
        super().__init__()
        self._mode = "mixed"
        self.setFixedHeight(218)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_mode(self, mode: str):
        self._mode = mode
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        W        = self.width()
        M        = 14          # outer margin
        GAP_H    = 18          # horizontal gap between columns (arrow space)
        GAP_V    = 28          # vertical gap between rows (arrow space)
        HDR_H    = 20
        CELL_H   = 72

        col_w   = (W - 2*M - 2*GAP_H) // 3
        y_before = M + HDR_H + 4
        y_after  = y_before + CELL_H + GAP_V

        after = self._AFTER.get(self._mode, self._AFTER["mixed"])

        # Column headers
        hdr_font = QFont(); hdr_font.setPointSize(10)
        p.setFont(hdr_font)
        p.setPen(QColor(TEXT_TERTIARY))
        for ci, title in enumerate(self._COLS):
            x = M + ci * (col_w + GAP_H)
            p.drawText(x, M, col_w, HDR_H, Qt.AlignHCenter | Qt.AlignVCenter, title)

        # Cells
        for ci in range(3):
            x = M + ci * (col_w + GAP_H)
            for row_i, (y, row_tag, states) in enumerate([
                (y_before, "BEFORE", self._BEFORE),
                (y_after,  "AFTER",  after),
            ]):
                text, color_hex, alpha = states[ci]
                bg = QColor(color_hex); bg.setAlpha(alpha)
                border_col = QColor(color_hex); border_col.setAlpha(160)

                p.setPen(QPen(border_col, 1.5))
                p.setBrush(QBrush(bg))
                p.drawRoundedRect(x, y, col_w, CELL_H, 7, 7)

                # Row tag (BEFORE / AFTER)
                tag_font = QFont(); tag_font.setPointSize(9); tag_font.setBold(True)
                p.setFont(tag_font)
                p.setPen(QColor(color_hex))
                p.drawText(x + 7, y + 5, col_w - 14, 16, Qt.AlignLeft, row_tag)

                # Content text
                ct_font = QFont(); ct_font.setPointSize(11)
                p.setFont(ct_font)
                p.drawText(
                    x + 4, y + 24, col_w - 8, CELL_H - 28,
                    Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, text,
                )

        # Horizontal arrows between BEFORE cells
        arr_pen = QPen(QColor(SEPARATOR), 1.5)
        p.setPen(arr_pen)
        p.setBrush(Qt.NoBrush)
        for ci in range(2):
            ax1 = M + (ci + 1) * col_w + ci * GAP_H + 2
            ax2 = ax1 + GAP_H - 4
            ay  = y_before + CELL_H // 2
            p.drawLine(ax1, ay, ax2 - 6, ay)
            p.drawLine(ax2 - 6, ay, ax2 - 11, ay - 4)
            p.drawLine(ax2 - 6, ay, ax2 - 11, ay + 4)

        # Vertical arrows for each column (between rows)
        for ci in range(3):
            ax = M + ci * (col_w + GAP_H) + col_w // 2
            ay1 = y_before + CELL_H + 4
            ay2 = y_after - 4
            p.drawLine(ax, ay1, ax, ay2 - 6)
            p.drawLine(ax, ay2 - 6, ax - 4, ay2 - 11)
            p.drawLine(ax, ay2 - 6, ax + 4, ay2 - 11)

        p.end()


class ResetVisualizerPanel(QDialog):
    """
    Phase 4.3 — Reset Visualizer.

    Four numbered steps enforce a safe review workflow:

      ① Specify a target ref + click "Preview on Graph"
            → emits reset_preview_requested → DagCanvas overlays red rings
      ② Pick a mode (Soft / Mixed / Hard)
            → StagingDiagram updates in real-time
      ③ Read the before/after diagram
      ④ Check the confirmation checkbox → Confirm Reset becomes active

    Safety rules
    ─────────────
    • Confirm is disabled until Preview has been run AND checkbox is checked.
    • Changing mode after preview clears the gates and requires re-preview.
    • Closing or cancelling always clears DAG overlays.
    • closeEvent also resets gates, so re-opening starts clean.
    """

    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state     = state
        self._previewed = False

        self.setWindowTitle("Reset Visualizer")
        self.setModal(False)
        self.resize(500, 720)
        self.setMinimumWidth(440)
        self.setStyleSheet(STYLESHEET)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background:transparent; border:none;")

        body = QWidget()
        body.setStyleSheet(f"background:{BG_BASE};")
        vbox = QVBoxLayout(body)
        vbox.setContentsMargins(18, 18, 18, 18)
        vbox.setSpacing(14)

        # ── Header ────────────────────────────────────────────────────────────
        vbox.addWidget(label("↩  Reset Visualizer", 17, TEXT_PRIMARY, 700))
        intro = QLabel(
            "Preview which commits will be removed from the branch and what "
            "happens to their changes — before anything is executed. "
            "Complete all four steps in order."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(
            f"color:{TEXT_TERTIARY}; font-size:12px; background:transparent;"
        )
        vbox.addWidget(intro)
        vbox.addWidget(h_separator())

        # ── Step 1: target + preview ──────────────────────────────────────────
        vbox.addWidget(label("①  Specify target and preview on graph",
                           13, TEXT_PRIMARY, 600))

        tr = QHBoxLayout(); tr.setSpacing(8)
        tr.addWidget(label("Target:", 12, TEXT_SECONDARY))
        self._target = QLineEdit("HEAD~1")
        self._target.setObjectName("rvTargetInput")
        self._target.setPlaceholderText("HEAD~1 · HEAD~3 · a commit SHA")
        tr.addWidget(self._target)
        vbox.addLayout(tr)

        pr = QHBoxLayout(); pr.setSpacing(8)
        self._preview_btn = QPushButton("Preview on Graph →")
        self._preview_btn.setObjectName("rvPreviewBtn")
        self._preview_btn.setFixedHeight(30)
        self._preview_btn.setEnabled(False)
        self._preview_btn.clicked.connect(self._do_preview)
        self._preview_status = label("", 11, TEXT_TERTIARY)
        pr.addWidget(self._preview_btn)
        pr.addWidget(self._preview_status)
        pr.addStretch()
        vbox.addLayout(pr)
        vbox.addWidget(h_separator())

        # ── Step 2: mode picker ───────────────────────────────────────────────
        vbox.addWidget(label("②  Choose a mode", 13, TEXT_PRIMARY, 600))

        self._mode_group  = QButtonGroup(self)
        self._mode_radios: dict[str, QRadioButton] = {}

        mode_defs = [
            ("soft",  "Soft",
             "Changes from removed commits land in the index — staged and "
             "ready to re-commit. Nothing is lost; you can recommit immediately."),
            ("mixed", "Mixed  (default)",
             "Changes from removed commits land in the working directory — "
             "unstaged but intact. Index is cleared. Files are not touched."),
            ("hard",  "Hard  ⚠",
             "Working directory and index are reset to match the target. "
             "All changes from removed commits are permanently discarded. "
             "There is no recovery path without a reflog."),
        ]
        for i, (key, lbl, desc) in enumerate(mode_defs):
            card = QWidget()
            card.setObjectName("rvModeCard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 10, 12, 10)
            cl.setSpacing(4)

            rb = QRadioButton(lbl)
            rb.setChecked(key == "mixed")
            rb.setStyleSheet(
                f"color:{TEXT_PRIMARY}; font-size:13px; font-weight:600;"
                " background:transparent; spacing:8px;"
            )
            self._mode_group.addButton(rb, i)
            self._mode_radios[key] = rb

            d = QLabel(desc)
            d.setWordWrap(True)
            d.setStyleSheet(
                f"color:{TEXT_SECONDARY}; font-size:11px; background:transparent;"
            )
            cl.addWidget(rb)
            cl.addWidget(d)
            vbox.addWidget(card)

        self._mode_group.buttonToggled.connect(self._on_mode_changed)
        vbox.addWidget(h_separator())

        # ── Step 3: staging diagram ───────────────────────────────────────────
        vbox.addWidget(label("③  Effect on git areas — before and after",
                           13, TEXT_PRIMARY, 600))
        self._diagram = StagingDiagram()
        self._diagram.set_mode("mixed")
        vbox.addWidget(self._diagram)
        vbox.addWidget(h_separator())

        # ── Step 4: confirm gate ──────────────────────────────────────────────
        vbox.addWidget(label("④  Confirm to execute", 13, TEXT_PRIMARY, 600))

        self._warn = QLabel(
            "⚠  Commits highlighted in red on the graph will be removed "
            "from this branch. Click 'Preview on Graph' first."
        )
        self._warn.setObjectName("rvWarning")
        self._warn.setWordWrap(True)
        vbox.addWidget(self._warn)

        self._confirm_chk = QCheckBox(
            "I have reviewed the preview and understand what will be changed"
        )
        self._confirm_chk.setStyleSheet(
            f"color:{TEXT_PRIMARY}; font-size:12px; background:transparent; spacing:8px;"
        )
        self._confirm_chk.setEnabled(False)
        self._confirm_chk.stateChanged.connect(self._update_confirm_btn)
        vbox.addWidget(self._confirm_chk)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.clicked.connect(self._do_cancel)

        self._confirm_btn = QPushButton("Confirm Reset →")
        self._confirm_btn.setObjectName("rvConfirmBtn")
        self._confirm_btn.setFixedHeight(36)
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self._do_reset)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._confirm_btn)
        vbox.addLayout(btn_row)
        vbox.addStretch()

        scroll.setWidget(body)
        root.addWidget(scroll)

        state.repo_changed.connect(self._on_repo_changed)
        self._on_repo_changed(state.repo)

    # ── Repo change ───────────────────────────────────────────────────────────

    def _on_repo_changed(self, repo):
        self._preview_btn.setEnabled(repo is not None)
        if repo is None:
            self._reset_gates()

    # ── Mode change ───────────────────────────────────────────────────────────

    def _on_mode_changed(self):
        mode = self._current_mode()
        self._diagram.set_mode(mode)
        if self._previewed:
            # Mode change invalidates the current preview — require a re-run
            self._reset_gates()
            self._preview_status.setText("Mode changed — re-preview required")
            self._preview_status.setStyleSheet(
                f"color:{ACCENT_ORANGE}; font-size:11px; background:transparent;"
            )

    def _current_mode(self) -> str:
        for key, rb in self._mode_radios.items():
            if rb.isChecked():
                return key
        return "mixed"

    # ── Preview ───────────────────────────────────────────────────────────────

    def _do_preview(self):
        repo = self._state.repo
        if repo is None:
            return

        raw  = self._target.text().strip() or "HEAD~1"
        mode = self._current_mode()

        try:
            target_sha = repo.rev_parse(raw).hexsha
        except Exception as exc:
            self._preview_status.setText(f"Cannot resolve '{raw}': {exc}")
            self._preview_status.setStyleSheet(
                f"color:{ACCENT_RED}; font-size:11px; background:transparent;"
            )
            return

        # Signal DagCanvas to draw overlays
        self._state.reset_preview_requested.emit(target_sha, mode)

        # Count affected commits for the status label
        try:
            head = repo.head.commit.hexsha
            n = sum(1 for _ in repo.iter_commits(f"{target_sha}..{head}"))
        except Exception:
            n = 0

        self._previewed = True
        self._preview_status.setText(
            f"✓  {n} commit{'s' if n != 1 else ''} highlighted red on the graph"
        )
        self._preview_status.setStyleSheet(
            f"color:{ACCENT_GREEN}; font-size:11px; background:transparent;"
        )
        self._confirm_chk.setEnabled(True)
        self._state.logger.log(
            f"Reset preview: --{mode}  target={target_sha[:12]}  ({n} commit(s) affected)"
        )

    # ── Confirm gate ──────────────────────────────────────────────────────────

    def _update_confirm_btn(self):
        self._confirm_btn.setEnabled(
            self._previewed and self._confirm_chk.isChecked()
        )

    # ── Execute ───────────────────────────────────────────────────────────────

    def _do_reset(self):
        repo = self._state.repo
        if repo is None:
            return

        raw  = self._target.text().strip() or "HEAD~1"
        flag = f"--{self._current_mode()}"

        # Clear overlays first — the scene will be rebuilt by set_repo anyway
        self._state.reset_preview_cleared.emit()
        self._reset_gates()

        try:
            repo.git.reset(flag, raw)
            self._state.set_repo(repo)      # triggers full panel refresh
            self._state.logger.log(f"Reset {flag} to '{raw}'", "OK  ")
        except Exception as exc:
            self._state.logger.log(f"Reset failed: {exc}", "ERR ")

    # ── Cancel ────────────────────────────────────────────────────────────────

    def _do_cancel(self):
        self._state.reset_preview_cleared.emit()
        self._reset_gates()
        self.hide()

    def closeEvent(self, event):
        self._state.reset_preview_cleared.emit()
        self._reset_gates()
        super().closeEvent(event)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _reset_gates(self):
        """Return UI to pre-preview state without touching the mode selection."""
        self._previewed = False
        self._confirm_chk.setChecked(False)
        self._confirm_chk.setEnabled(False)
        self._confirm_btn.setEnabled(False)
        self._preview_status.setText("")



class ResetVisualizerDialog(QDialog):
    """
    Step 4.3 — Reset preview dialog.

    Opened by TimeTravelPanel BEFORE any git reset runs.
    Shows two information areas:
      1. _ResetDagPreview  — which commits will be removed from the branch.
      2. _ModeStateDiagram — what happens to Working Dir / Index / History.

    The "Confirm Reset" button (red, explicit label) is the only path to
    QDialog.Accepted.  Closing the window or clicking Cancel returns Rejected —
    the caller must check the return value before executing anything.

    Invariant: this class never calls git.reset().  It is read-only.
    """

    _DESCRIPTIONS = {
        0: ("--soft",  ACCENT_GREEN,
            "The branch pointer moves back. All changes from the removed commits "
            "remain staged in the index — you can re-commit them immediately."),
        1: ("--mixed", ACCENT_ORANGE,
            "The branch pointer moves back. Changes are preserved in your working "
            "directory but are no longer staged — you must git add before committing."),
        2: ("--hard",  ACCENT_RED,
            "The branch pointer moves back and your working directory is overwritten "
            "to match the target commit. All uncommitted and unstaged changes are "
            "permanently deleted with no recovery path."),
    }

    def __init__(self, repo, target: str, mode_id: int, parent=None):
        super().__init__(parent)
        flag_str, accent, description = self._DESCRIPTIONS[mode_id]

        self.setWindowTitle(f"Preview: git reset {flag_str} {target}")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setStyleSheet(STYLESHEET)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # ── Operation header ──────────────────────────────────────────────────
        cmd_row = QHBoxLayout()
        mode_badge = QLabel(f" {flag_str} ")
        mode_badge.setStyleSheet(
            f"color:white; background:{accent}; border-radius:4px;"
            " font-size:12px; font-weight:700; padding:2px 8px;"
        )
        cmd_row.addWidget(mode_badge)
        cmd_row.addWidget(label(f"git reset {flag_str} {target}", 14, TEXT_PRIMARY, 700))
        cmd_row.addStretch()
        root.addLayout(cmd_row)

        desc = QLabel(description)
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color:{TEXT_SECONDARY}; font-size:12px; background:transparent;"
        )
        root.addWidget(desc)
        root.addWidget(h_separator())

        # ── DAG commit preview ────────────────────────────────────────────────
        root.addWidget(label("Commits that will be removed:", 11, TEXT_TERTIARY, 600))

        dag = _ResetDagPreview()
        removed, target_commit = self._resolve_commits(repo, target)
        target_msg = (target_commit.message.split("\n")[0]
                      if target_commit else "(could not resolve)")
        target_sha = target_commit.hexsha if target_commit else ""
        dag.set_data(
            [(c.hexsha, c.message.split("\n")[0]) for c in removed],
            target_sha, target_msg,
        )
        root.addWidget(dag)

        # Commit count summary
        n = len(removed)
        summary = label(
            (f"{n} commit{'s' if n != 1 else ''} will be removed from this branch."
             if n else "HEAD is already at the target — no commits would be removed."),
            12,
            ACCENT_ORANGE if n else TEXT_TERTIARY,
            500,
        )
        summary.setObjectName("resetSummaryLabel")
        root.addWidget(summary)
        root.addWidget(h_separator())

        # ── State diagram ─────────────────────────────────────────────────────
        root.addWidget(label("Effect on your files:", 11, TEXT_TERTIARY, 600))
        diagram = _ModeStateDiagram()
        diagram.set_mode(mode_id)
        root.addWidget(diagram)

        # ── Hard-mode extra warning ───────────────────────────────────────────
        if mode_id == 2:
            warn = QWidget()
            warn.setObjectName("resetWarnBox")
            wl  = QHBoxLayout(warn)
            wl.setContentsMargins(12, 10, 12, 10)
            w_lbl = QLabel(
                "⚠  Hard reset is irreversible. Any file changes not recorded "
                "in a commit will be permanently lost — there is no undo."
            )
            w_lbl.setWordWrap(True)
            w_lbl.setStyleSheet(
                f"color:{ACCENT_RED}; font-size:12px; background:transparent;"
            )
            wl.addWidget(w_lbl)
            root.addWidget(warn)

        root.addWidget(h_separator())

        # ── Buttons ───────────────────────────────────────────────────────────
        btns = QHBoxLayout()
        btns.addStretch()

        cancel = QPushButton("Cancel")
        cancel.setObjectName("resetCancelBtn")
        cancel.setFixedHeight(34)
        cancel.clicked.connect(self.reject)

        # Label includes the full command so there is zero ambiguity about
        # what pressing this button will execute
        confirm = QPushButton(f"⚠  Confirm:  git reset {flag_str} {target}")
        confirm.setObjectName("resetConfirmBtn")
        confirm.setFixedHeight(34)
        confirm.clicked.connect(self.accept)

        btns.addWidget(cancel)
        btns.addSpacing(8)
        btns.addWidget(confirm)
        root.addLayout(btns)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_commits(repo, target: str) -> "tuple[list, object | None]":
        """Return (removed_commits_list, target_commit_object)."""
        removed = []
        target_obj = None
        try:
            removed = list(repo.iter_commits(f"{target}..HEAD", max_count=50))
        except Exception:
            pass
        try:
            target_obj = repo.rev_parse(target)
        except Exception:
            pass
        return removed, target_obj
    



class _SectionCard(QWidget):

    def __init__(self, number: str, title: str, description: str, accent: str):
        super().__init__()
        self.setObjectName("ttCard")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setObjectName("ttCard")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(16, 14, 16, 16)
        fl.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)
        badge = QLabel(number)
        badge.setFixedSize(22, 22)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"background:{accent}; color:white; border-radius:11px;"
            " font-size:11px; font-weight:700;"
        )
        header.addWidget(badge)
        header.addWidget(label(title, 14, TEXT_PRIMARY, 600))
        header.addStretch()
        fl.addLayout(header)
        fl.addWidget(h_separator())

        desc = QLabel(description)
        desc.setObjectName("ttDesc")
        desc.setWordWrap(True)
        fl.addWidget(desc)
        fl.addWidget(h_separator())

        self._controls = QVBoxLayout()
        self._controls.setSpacing(8)
        fl.addLayout(self._controls)

        outer.addWidget(frame)

    @property
    def controls(self) -> QVBoxLayout:
        return self._controls




class TimeTravelPanel(QDialog):
    """
    Non-modal dialog with three collapsible operation cards:

      1.  Checkout : move HEAD to any ref (branch, tag, or bare SHA).
      2.  Reset    : rewrite branch history; soft / mixed / hard modes.
      3.  Revert   : add an inverse commit that safely undoes a past change.
    """

    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self.setWindowTitle("Time Travel")
        self.setModal(False)                # non-modal: graph stays interactive
        self.resize(520, 800)
        self.setMinimumWidth(440)
        self.setStyleSheet(STYLESHEET)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background:transparent; border:none;")

        body = QWidget()
        body.setStyleSheet(f"background:{BG_BASE};")
        vbox = QVBoxLayout(body)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(14)


        vbox.addWidget(label("⏱  Time Travel", 17, TEXT_PRIMARY, 700))

        intro = QLabel(
            "Explore, undo, and reshape Git history using three operations. "
            "Each section describes exactly what the command does before "
            "offering controls. Read the description first, especially for "
            "'Reset', which can permanently discard work."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(
            f"color:{TEXT_TERTIARY}; font-size:12px; background:transparent;"
        )
        vbox.addWidget(intro)
        vbox.addWidget(h_separator())

        # Operation cards
        vbox.addWidget(self._build_checkout_card())
        vbox.addWidget(self._build_reset_card())
        vbox.addWidget(self._build_revert_card())

        # Result log
        vbox.addWidget(h_separator())
        vbox.addWidget(label("Last Result", 11, TEXT_TERTIARY, 600))
        self._result = QPlainTextEdit()
        self._result.setObjectName("ttResultArea")
        self._result.setReadOnly(True)
        self._result.setFixedHeight(76)
        self._result.setPlaceholderText("No operation run yet in this session.")
        vbox.addWidget(self._result)
        vbox.addStretch()

        scroll.setWidget(body)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        state.repo_changed.connect(self._on_repo_changed)
        self._on_repo_changed(state.repo)       # populate on first open


    def _build_checkout_card(self) -> _SectionCard:
        card = _SectionCard(
            "①", "Checkout",
            "Moves HEAD and your working directory to any commit, branch, "
            "or tag you specify.\n\n"
            "Pointing to a branch name (e.g. main) keeps you attached to that "
            "branch: future commits advance it normally. Pointing to a bare "
            "commit SHA enters detached HEAD state — you can explore and "
            "experiment freely, but any commits you make will be orphaned "
            "unless you first create a new branch"
            "with 'git switch -c <new-branch>'.",
            ACCENT_GREEN,
        )

        ref_row = QHBoxLayout()
        ref_row.setSpacing(8)
        ref_row.addWidget(label("Target:", 12, TEXT_SECONDARY))
        self._co_combo = QComboBox()
        self._co_combo.setObjectName("ttCombo")
        self._co_combo.setEditable(True)
        self._co_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._co_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._co_combo.setPlaceholderText("branch, tag, or SHA…")
        self._co_combo.currentTextChanged.connect(self._on_co_changed)
        ref_row.addWidget(self._co_combo)
        card.controls.addLayout(ref_row)

        # Detached-HEAD advisory
        self._co_warn = QLabel(
            "⚠  Checking out a bare SHA will detach HEAD.  "
            "Create a branch before making new commits."
        )
        self._co_warn.setObjectName("ttWarning")
        self._co_warn.setWordWrap(True)
        self._co_warn.hide()
        card.controls.addWidget(self._co_warn)

        self._co_btn = QPushButton("Checkout →")
        self._co_btn.setFixedHeight(32)
        self._co_btn.setEnabled(False)
        self._co_btn.clicked.connect(self._do_checkout)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._co_btn)
        card.controls.addLayout(btn_row)

        return card

    def _build_reset_card(self) -> _SectionCard:
        card = _SectionCard(
            "②", "Reset",
            "Moves the current branch's tip to a different commit, rewriting "
            "its history. Three modes control what happens to your changes:\n\n"
            "  Soft  — changes remain staged, ready to re-commit.\n"
            "  Mixed — changes are unstaged but files are preserved (default).\n"
            "  Hard  — staged and unstaged changes are permanently discarded. "
            "The working directory is overwritten with no recovery path.\n\n"
            "⚠  Never reset commits that are already on a shared remote — "
            "rewriting public history causes conflicts for every collaborator.",
            ACCENT_ORANGE,
        )

        # Target ref input
        target_row = QHBoxLayout()
        target_row.setSpacing(8)
        target_row.addWidget(label("Target:", 12, TEXT_SECONDARY))
        self._re_input = QLineEdit("HEAD~1")
        self._re_input.setObjectName("ttInput")
        self._re_input.setPlaceholderText("e.g. HEAD~2  or  a commit SHA")
        target_row.addWidget(self._re_input)
        card.controls.addLayout(target_row)

        # Soft / Mixed / Hard radio buttons
        mode_row = QHBoxLayout()
        mode_row.setSpacing(16)
        mode_row.addWidget(label("Mode:", 12, TEXT_SECONDARY))
        self._re_group = QButtonGroup(self)
        mode_meta = [
            ("Soft",  "Keeps staged changes"),
            ("Mixed", "Unstages changes, keeps files (default)"),
            ("Hard",  "⚠  Permanently discards all changes"),
        ]
        for i, (lbl, tip) in enumerate(mode_meta):
            rb = QRadioButton(lbl)
            rb.setToolTip(tip)
            self._re_group.addButton(rb, i)
            mode_row.addWidget(rb)
        self._re_group.button(0).setChecked(True)
        self._re_group.buttonToggled.connect(self._on_reset_mode_changed)
        mode_row.addStretch()
        card.controls.addLayout(mode_row)

        # Hard-reset confirmation gate
        self._re_confirm = QCheckBox(
            "I understand this permanently discards all uncommitted changes"
        )
        self._re_confirm.setStyleSheet(
            f"color:{ACCENT_RED}; font-size:11px; background:transparent; spacing:6px;"
        )
        self._re_confirm.hide()
        self._re_confirm.stateChanged.connect(self._update_reset_btn)
        card.controls.addWidget(self._re_confirm)


        # Change the button label and its click connection:
        self._re_btn = QPushButton("Preview Reset →")          # was "Reset →"
        self._re_btn.setFixedHeight(32)
        self._re_btn.setEnabled(False)
        self._re_btn.clicked.connect(self._preview_reset)      # was self._do_reset

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._re_btn)
        card.controls.addLayout(btn_row)

        return card

    def _build_revert_card(self) -> _SectionCard:
        card = _SectionCard(
            "③", "Revert",
            "Creates a brand-new commit whose changes are the exact inverse of "
            "the commit you specify — undoing that commit without touching "
            "history.\n\n"
            "Because revert only adds a new commit rather than rewriting "
            "existing ones, it is completely safe on branches that others "
            "are working from. This is the correct tool whenever you need "
            "to undo something that has already been pushed to a shared remote.",
            ACCENT,
        )

        sha_row = QHBoxLayout()
        sha_row.setSpacing(8)
        sha_row.addWidget(label("SHA:", 12, TEXT_SECONDARY))
        self._rv_input = QLineEdit()
        self._rv_input.setObjectName("ttInput")
        self._rv_input.setPlaceholderText("Full or partial commit SHA to revert")
        self._rv_input.textChanged.connect(
            lambda t: self._rv_btn.setEnabled(
                self._state.repo is not None and bool(t.strip())
            )
        )
        sha_row.addWidget(self._rv_input)
        card.controls.addLayout(sha_row)

        self._rv_btn = QPushButton("Revert →")
        self._rv_btn.setFixedHeight(32)
        self._rv_btn.setEnabled(False)
        self._rv_btn.clicked.connect(self._do_revert)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._rv_btn)
        card.controls.addLayout(btn_row)

        return card

    # Repo state
    def _on_repo_changed(self, repo):
        has = repo is not None

        self._co_combo.clear()
        if has:
            try:
                for b in repo.branches:
                    self._co_combo.addItem(f"⎇  {b.name}", userData=b.name)
                for t in repo.tags:
                    self._co_combo.addItem(f"◇  {t.name}", userData=t.name)
            except Exception:
                pass

        self._co_btn.setEnabled(has and bool(self._co_combo.currentText()))
        self._re_btn.setEnabled(has and self._re_group.checkedId() != 2)
        self._rv_btn.setEnabled(False)
        self._re_confirm.setChecked(False)
        self._re_confirm.hide()



    def _on_co_changed(self, text: str):
        """Show detached-HEAD advisory when the text looks like a raw SHA."""
        is_sha = bool(text) and all(c in "0123456789abcdefABCDEF" for c in text)
        self._co_warn.setVisible(is_sha)
        self._co_btn.setEnabled(self._state.repo is not None and bool(text.strip()))


    def _on_reset_mode_changed(self):
        hard = (self._re_group.checkedId() == 2)
        self._re_confirm.setVisible(hard)
        self._update_reset_btn()


    def _update_reset_btn(self):
        if self._state.repo is None:
            self._re_btn.setEnabled(False)
            return
        hard = (self._re_group.checkedId() == 2)
        self._re_btn.setEnabled(not hard or self._re_confirm.isChecked())



    def _preview_reset(self):
        """
        Open the reset visualizer dialog.
        Only calls _execute_reset() if the user explicitly clicks Confirm.
        Never executes git reset automatically.
        """
        repo = self._state.repo
        if repo is None:
            return

        mode_id = self._re_group.checkedId()
        target  = self._re_input.text().strip() or "HEAD~1"

        # Gate: hard reset still requires the checkbox (first confirmation layer)
        if mode_id == 2 and not self._re_confirm.isChecked():
            return

        dlg = ResetVisualizerDialog(repo, target, mode_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            # User saw the preview AND clicked the explicit confirm button
            self._execute_reset(mode_id, target)

    def _do_checkout(self):
        repo = self._state.repo
        if repo is None:
            return

        raw = self._co_combo.currentText().strip()
        ref = raw.lstrip("⎇◇ ")
        self._show("$ git checkout " + ref, TEXT_TERTIARY)
        try:
            repo.git.checkout(ref)
            self._state.set_repo(repo)
            self._show(f"[OK]  Checked out '{ref}'", ACCENT_GREEN)
            self._state.logger.log(f"Checkout → {ref}", "OK  ")
        except Exception as exc:
            self._show(f"[ERR]  {exc}", ACCENT_RED)
            self._state.logger.log(f"Checkout failed: {exc}", "ERR ")



    def _execute_reset(self, mode_id: int, target: str):
        """
        Execute git reset.  Called only after ResetVisualizerDialog.Accepted.
        This is the sole write path for reset — never called directly from UI.
        """
        repo = self._state.repo
        if repo is None:
            return

        modes = {0: "--soft", 1: "--mixed", 2: "--hard"}
        mode  = modes[mode_id]

        self._show(f"$ git reset {mode} {target}", TEXT_TERTIARY)
        try:
            repo.git.reset(mode, target)
            self._state.set_repo(repo)          # re-emit → all panels + DAG refresh
            self._re_confirm.setChecked(False)  # clear hard-reset gate
            self._show(f"✓  Reset {mode} to '{target}'", ACCENT_GREEN)
            self._state.logger.log(f"Reset {mode} → {target}", "OK  ")
        except Exception as exc:
            self._show(f"✗  {exc}", ACCENT_RED)
            self._state.logger.log(f"Reset failed: {exc}", "ERR ")

    def _do_revert(self):
        repo = self._state.repo
        if repo is None:
            return
        sha = self._rv_input.text().strip()
        self._show(f"$ git revert {sha}", TEXT_TERTIARY)
        try:
            repo.git.revert(sha, no_edit=True)
            self._state.set_repo(repo)
            self._rv_input.clear()
            self._show(f"[OK]  Reverted {sha[:12]}", ACCENT_GREEN)
            self._state.logger.log(f"Revert: {sha[:12]}", "OK  ")
        except Exception as exc:
            self._show(f"[ERR]  {exc}", ACCENT_RED)
            self._state.logger.log(f"Revert failed: {exc}", "ERR ")



    def _show(self, msg: str, color: str):
        """Append a result line and auto-scroll."""
        html = f"<span style='color:{color};'>{msg}</span>"
        self._result.appendHtml(html)
        sb = self._result.verticalScrollBar()
        sb.setValue(sb.maximum())