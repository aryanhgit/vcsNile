from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QCheckBox, QDialog,
)

from ui.resources.theme import STYLESHEET
from ui.resources.constants import (ACCENT, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED, BG_BASE, 
                                    BG_PANEL, SEPARATOR, TEXT_PRIMARY, TEXT_TERTIARY, TEXT_SECONDARY)
from utils.helper import label, h_separator
from utils.state import AppState


class RevertWalkthroughPanel(QDialog):
    """
    Non-modal walkthrough for git revert.
    """

    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state     = state
        self._previewed = False

        self.setWindowTitle("Revert Walkthrough")
        self.setModal(False)
        self.resize(480, 580)
        self.setMinimumWidth(400)
        self.setStyleSheet(STYLESHEET)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        root.addWidget(label("⏮  Revert Walkthrough", 17, TEXT_PRIMARY, 700))

        expl = QLabel(
            "git revert creates a brand-new commit whose diff is the exact "
            "inverse of the commit you select. The original commit stays in "
            "history unchanged i.e nothing is rewritten. This makes revert "
            "the correct tool for undoing changes that have already been "
            "pushed to a shared remote.\n\n"
            "The preview shows the new commit node that will appear at the "
            "top of the graph, connected by a dashed 'reverts' arrow to "
            "the commit being undone."
        )
        expl.setWordWrap(True)
        expl.setStyleSheet(
            f"color:{TEXT_SECONDARY}; font-size:12px; background:transparent;"
        )
        root.addWidget(expl)
        root.addWidget(h_separator())

        # SHA + preview
        root.addWidget(label("①  Select the commit to revert", 13, TEXT_PRIMARY, 600))

        sha_row = QHBoxLayout(); sha_row.setSpacing(8)
        sha_row.addWidget(label("SHA:", 12, TEXT_SECONDARY))
        self._sha_input = QLineEdit()
        self._sha_input.setObjectName("rvTargetInput")
        self._sha_input.setPlaceholderText("Full or partial commit SHA")
        self._sha_input.textChanged.connect(self._on_sha_changed)
        sha_row.addWidget(self._sha_input)
        root.addLayout(sha_row)

        prev_row = QHBoxLayout(); prev_row.setSpacing(8)
        self._preview_btn = QPushButton("Preview on Graph →")
        self._preview_btn.setObjectName("rvPreviewBtn")
        self._preview_btn.setFixedHeight(30)
        self._preview_btn.setEnabled(False)
        self._preview_btn.clicked.connect(self._do_preview)
        self._preview_status = label("", 11, TEXT_TERTIARY)
        prev_row.addWidget(self._preview_btn)
        prev_row.addWidget(self._preview_status)
        prev_row.addStretch()
        root.addLayout(prev_row)
        root.addWidget(h_separator())

        # effect summary
        root.addWidget(label("②  What will happen", 13, TEXT_PRIMARY, 600))

        card = QWidget()
        card.setStyleSheet(
            f"background:{BG_PANEL}; border-radius:8px; border:1px solid {SEPARATOR};"
        )
        cl = QVBoxLayout(card); cl.setContentsMargins(14, 12, 14, 12)
        self._effect_lbl = QLabel("Enter a SHA and click Preview to see details.")
        self._effect_lbl.setWordWrap(True)
        self._effect_lbl.setStyleSheet(
            f"color:{TEXT_SECONDARY}; font-size:12px; background:transparent;"
        )
        cl.addWidget(self._effect_lbl)
        root.addWidget(card)
        root.addWidget(h_separator())

        # confirmation gate
        root.addWidget(label("③  Confirm to execute", 13, TEXT_PRIMARY, 600))

        self._confirm_chk = QCheckBox(
            "I have reviewed the graph preview and understand what will change"
        )
        self._confirm_chk.setStyleSheet(
            f"color:{TEXT_PRIMARY}; font-size:12px; background:transparent; spacing:8px;"
        )
        self._confirm_chk.setEnabled(False)
        self._confirm_chk.stateChanged.connect(self._update_confirm_btn)
        root.addWidget(self._confirm_chk)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.clicked.connect(self._do_cancel)

        self._confirm_btn = QPushButton("Confirm Revert →")
        self._confirm_btn.setObjectName("rvConfirmBtn")
        self._confirm_btn.setFixedHeight(34)
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self._do_revert)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._confirm_btn)
        root.addLayout(btn_row)
        root.addStretch()

        state.repo_changed.connect(self._on_repo_changed)
        self._on_repo_changed(state.repo)


    def _on_repo_changed(self, _repo):
        self._sha_input.clear()
        self._reset_gates()

    def _on_sha_changed(self, text: str):
        self._preview_btn.setEnabled(
            self._state.repo is not None and bool(text.strip())
        )
        if self._previewed:
            self._reset_gates()

    def _do_preview(self):
        repo = self._state.repo
        if repo is None:
            return
        raw = self._sha_input.text().strip()
        try:
            target_sha = repo.rev_parse(raw).hexsha
        except Exception as exc:
            self._preview_status.setText(f"Cannot resolve: {exc}")
            return

        self._state.revert_preview_requested.emit(target_sha)

        try:
            commit     = repo.commit(target_sha)
            n_files    = len(commit.stats.files)
            short_msg  = commit.message.split("\n")[0][:52]
            branch     = self._state.active_branch
            self._effect_lbl.setText(
                f"A new commit will appear at the top of branch '{branch}'.\n\n"
                f"It will reverse the {n_files} file change(s) introduced by:\n"
                f"  {target_sha[:12]}  \"{short_msg}\"\n\n"
                f"The original commit stays in history — history is not rewritten."
            )
        except Exception:
            self._effect_lbl.setText("Preview set on graph. Confirm to execute.")

        self._previewed = True
        self._preview_status.setText("[OK] Ghost node drawn on graph")
        self._preview_status.setStyleSheet(
            f"color:{ACCENT_GREEN}; font-size:11px; background:transparent;"
        )
        self._confirm_chk.setEnabled(True)
        self._state.logger.log(f"Revert preview: target={target_sha[:12]}")

    def _update_confirm_btn(self):
        self._confirm_btn.setEnabled(
            self._previewed and self._confirm_chk.isChecked()
        )

    def _do_revert(self):
        repo = self._state.repo
        if repo is None:
            return
        raw = self._sha_input.text().strip()
        self._state.revert_preview_cleared.emit()
        self._reset_gates()
        try:
            repo.git.revert(raw, no_edit=True)
            self._state.set_repo(repo)
            self._state.logger.log(f"Reverted {raw[:12]}", "OK  ")
        except Exception as exc:
            self._state.logger.log(f"Revert failed: {exc}", "ERR ")

    def _do_cancel(self):
        self._state.revert_preview_cleared.emit()
        self._reset_gates()
        self.hide()

    def closeEvent(self, event):
        self._state.revert_preview_cleared.emit()
        self._reset_gates()
        super().closeEvent(event)

    def _reset_gates(self):
        self._previewed = False
        self._confirm_chk.setChecked(False)
        self._confirm_chk.setEnabled(False)
        self._confirm_btn.setEnabled(False)
        self._preview_status.setText("")