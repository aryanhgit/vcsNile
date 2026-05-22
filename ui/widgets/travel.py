from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPlainTextEdit, QLineEdit, QFrame, QPushButton, QSizePolicy, QScrollArea, 
    QRadioButton, QCheckBox, QButtonGroup, QComboBox, QDialog,
)

from ui.resources.theme import STYLESHEET
from ui.resources.constants import (ACCENT, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED, BG_BASE, TEXT_PRIMARY, TEXT_TERTIARY, TEXT_SECONDARY)
from utils.helper import label, h_separator
from utils.state import AppState

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

        self._re_btn = QPushButton("Reset →")
        self._re_btn.setFixedHeight(32)
        self._re_btn.setEnabled(False)
        self._re_btn.clicked.connect(self._do_reset)
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



    def _do_reset(self):
        repo = self._state.repo
        if repo is None:
            return
        modes  = {0: "--soft", 1: "--mixed", 2: "--hard"}
        mode   = modes[self._re_group.checkedId()]
        target = self._re_input.text().strip() or "HEAD~1"
        self._show(f"$ git reset {mode} {target}", TEXT_TERTIARY)
        try:
            repo.git.reset(mode, target)
            self._state.set_repo(repo)
            self._re_confirm.setChecked(False)
            self._show(f"[OK]  Reset {mode} to '{target}'", ACCENT_GREEN)
            self._state.logger.log(f"Reset {mode} → {target}", "OK  ")
        except Exception as exc:
            self._show(f"[ERR]  {exc}", ACCENT_RED)
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