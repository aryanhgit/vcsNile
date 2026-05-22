from datetime import datetime
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget, 
    QLabel, QPlainTextEdit, QTreeWidget, QHeaderView, QTreeWidgetItem, QScrollArea, QLineEdit
)

from git_backend.state import AppState
from ui.resources.constants import (
    ACCENT, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED,
    BG_PANEL, TEXT_PRIMARY, TEXT_TERTIARY,
)
from utils.helper import h_separator, label


class BlobRenderer(QWidget):
    """
    Renders a blob object as a read-only monospace code view.
    """

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self._editor = QPlainTextEdit()
        self._editor.setObjectName("objBlobEditor")
        self._editor.setReadOnly(True)
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        f = QFont()
        f.setFamilies(["SF Mono", "Menlo", "Consolas", "Courier New"])
        f.setPointSize(12)
        self._editor.setFont(f)
        lay.addWidget(self._editor)

    def show_blob(self, blob):
        try:
            text = blob.data_stream.read().decode("utf-8", errors="replace")
        except Exception as exc:
            text = f"<binary — {blob.size} bytes>\n\n{exc}"
        self._editor.setPlainText(text)


class TreeRenderer(QWidget):
    """
    Renders a tree object as a three-column table.
    Clicking a SHA cell in the last column navigates to that object.
    """

    sha_clicked = Signal(str)

    _HEADERS = ["Mode", "Type", "Name", "SHA"]
    _COL_SHA = 3

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self._tree = QTreeWidget()
        self._tree.setObjectName("objTreeView")
        self._tree.setHeaderLabels(self._HEADERS)
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSortingEnabled(True)

        hdr = self._tree.header()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Mode
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Type
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)           # Name
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # SHA
        hdr.setStretchLastSection(False)

        self._tree.itemClicked.connect(self._on_item_clicked)
        lay.addWidget(self._tree)

    def show_tree(self, tree_obj):
        self._tree.clear()
        type_colors = {"blob": ACCENT, "tree": ACCENT_GREEN}
        for child in tree_obj:                       # direct children only
            mode = oct(child.mode)[2:]
            it = QTreeWidgetItem([
                mode, child.type, child.name, child.hexsha[:12],
            ])
            it.setData(self._COL_SHA, Qt.ItemDataRole.UserRole, child.hexsha)   # full SHA
            it.setForeground(1, QColor(type_colors.get(child.type, TEXT_TERTIARY)))
            it.setForeground(3, QColor(ACCENT))                    # SHA clickable hint
            it.setToolTip(3, f"Click to inspect  {child.hexsha}")
            self._tree.addTopLevelItem(it)

    def _on_item_clicked(self, item: QTreeWidgetItem, col: int):
        if col == self._COL_SHA:
            sha = item.data(col, Qt.ItemDataRole.UserRole)
            if sha:
                self.sha_clicked.emit(sha)



class CommitRenderer(QWidget):
    """
    Renders a commit object as a structured form.
    Tree SHA and parent SHAs are rendered as clickable HTML links.
    """

    sha_clicked = Signal(str)

    _FIELDS = ("SHA", "Tree", "Parent(s)", "Author", "Authored",
               "Committer", "Committed")

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background:transparent; border:none;")

        body = QWidget()
        body.setStyleSheet(f"background:{BG_PANEL};")
        vbox = QVBoxLayout(body)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(10)

        self._fields: dict[str, QLabel] = {}
        for key in self._FIELDS:
            row = QHBoxLayout()
            row.addWidget(label(key, 11, TEXT_TERTIARY, 600))
            row.addStretch()
            val = QLabel("—")
            val.setTextFormat(Qt.TextFormat.RichText)
            val.setOpenExternalLinks(False)
            val.setWordWrap(True)
            val.setStyleSheet(
                f"color:{TEXT_PRIMARY}; font-size:12px; background:transparent;"
            )
            val.linkActivated.connect(self.sha_clicked)
            self._fields[key] = val
            row.addWidget(val)
            vbox.addLayout(row)

        vbox.addSpacing(6)
        vbox.addWidget(h_separator())
        vbox.addWidget(label("Message", 11, TEXT_TERTIARY, 600))

        self._msg = QPlainTextEdit()
        self._msg.setObjectName("objCommitMsg")
        self._msg.setReadOnly(True)
        self._msg.setFixedHeight(110)
        f = QFont(); f.setFamilies(["SF Mono","Menlo","Consolas"]); f.setPointSize(12)
        self._msg.setFont(f)
        vbox.addWidget(self._msg)
        vbox.addStretch()

        scroll.setWidget(body)
        root.addWidget(scroll)

    def show_commit(self, commit):
        def link(sha: str) -> str:
            return (f"<a href='{sha}' style='color:{ACCENT};"
                    f" text-decoration:none;'>{sha[:12]}</a>")

        self._fields["SHA"].setText(
            f"<span style='font-family:monospace'>{commit.hexsha}</span>"
        )
        self._fields["Tree"].setText(link(commit.tree.hexsha))

        if commit.parents:
            self._fields["Parent(s)"].setText(
                "&nbsp;&nbsp;".join(link(p.hexsha) for p in commit.parents)
            )
        else:
            self._fields["Parent(s)"].setText(
                f"<span style='color:{TEXT_TERTIARY}'>(root commit)</span>"
            )

        self._fields["Author"].setText(
            f"{commit.author.name}  "
            f"<span style='color:{TEXT_TERTIARY}'>&lt;{commit.author.email}&gt;</span>"
        )
        self._fields["Authored"].setText(str(commit.authored_datetime))
        self._fields["Committer"].setText(
            f"{commit.committer.name}  "
            f"<span style='color:{TEXT_TERTIARY}'>&lt;{commit.committer.email}&gt;</span>"
        )
        self._fields["Committed"].setText(str(commit.committed_datetime))
        self._msg.setPlainText(commit.message.strip())



class TagRenderer(QWidget):
    """
    Renders an annotated tag object.
    The tagged object SHA is a clickable link.
    """

    sha_clicked = Signal(str)

    _FIELDS = ("Tag Name", "Tagger", "Date", "Object Type", "Object SHA")

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background:transparent; border:none;")

        body = QWidget()
        body.setStyleSheet(f"background:{BG_PANEL};")
        vbox = QVBoxLayout(body)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(10)

        self._fields: dict[str, QLabel] = {}
        for key in self._FIELDS:
            row = QHBoxLayout()
            row.addWidget(label(key, 11, TEXT_TERTIARY, 600))
            row.addStretch()
            val = QLabel("—")
            val.setTextFormat(Qt.TextFormat.RichText)
            val.setOpenExternalLinks(False)
            val.setStyleSheet(
                f"color:{TEXT_PRIMARY}; font-size:12px; background:transparent;"
            )
            val.linkActivated.connect(self.sha_clicked)
            self._fields[key] = val
            row.addWidget(val)
            vbox.addLayout(row)

        vbox.addSpacing(6)
        vbox.addWidget(h_separator())
        vbox.addWidget(label("Tag Message", 11, TEXT_TERTIARY, 600))

        self._msg = QPlainTextEdit()
        self._msg.setObjectName("objTagMsg")
        self._msg.setReadOnly(True)
        self._msg.setFixedHeight(80)
        vbox.addWidget(self._msg)
        vbox.addStretch()

        scroll.setWidget(body)
        root.addWidget(scroll)

    def show_tag(self, tag_obj):
        def link(sha: str) -> str:
            return (f"<a href='{sha}' style='color:{ACCENT};"
                    f" text-decoration:none;'>{sha[:12]}</a>")

        self._fields["Tag Name"].setText(tag_obj.tag)
        self._fields["Tagger"].setText(
            f"{tag_obj.tagger.name}  "
            f"<span style='color:{TEXT_TERTIARY}'>&lt;{tag_obj.tagger.email}&gt;</span>"
        )
        self._fields["Date"].setText(str(datetime.fromtimestamp(tag_obj.tagged_date)))
        self._fields["Object Type"].setText(tag_obj.object.type)
        self._fields["Object SHA"].setText(link(tag_obj.object.hexsha))
        self._msg.setPlainText(tag_obj.message.strip() if tag_obj.message else "")

class ObjectExplorerTab(QWidget):
   
    _PAGE_EMPTY, _PAGE_BLOB, _PAGE_TREE, _PAGE_COMMIT, _PAGE_TAG = range(5)

    _TYPE_COLORS = {
        "blob":   ACCENT,
        "tree":   ACCENT_GREEN,
        "commit": ACCENT_ORANGE,
        "tag":    ACCENT_RED,
    }

    def __init__(self, state: AppState):
        super().__init__()
        self._state   = state
        self._history: list[str] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # SHA input bar
        bar = QWidget()
        bar.setObjectName("objInputBar")
        bl  = QHBoxLayout(bar)
        bl.setContentsMargins(12, 8, 12, 8)
        bl.setSpacing(6)

        self._back_btn = QPushButton("← Back")
        self._back_btn.setObjectName("objBackBtn")
        self._back_btn.setFixedHeight(28)
        self._back_btn.setEnabled(False)
        self._back_btn.clicked.connect(self._go_back)

        self._sha_input = QLineEdit()
        self._sha_input.setObjectName("objShaInput")
        self._sha_input.setPlaceholderText(
            "Paste or type a SHA (full or partial) and press Enter…"
        )
        self._sha_input.returnPressed.connect(self._lookup)

        lookup_btn = QPushButton("Lookup")
        lookup_btn.setObjectName("objLookupBtn")
        lookup_btn.setFixedHeight(28)
        lookup_btn.clicked.connect(self._lookup)

        bl.addWidget(self._back_btn)
        bl.addWidget(self._sha_input)
        bl.addWidget(lookup_btn)
        root.addWidget(bar)
        root.addWidget(h_separator())

        # Breadcrumb trail
        self._crumb_bar = QWidget()
        self._crumb_bar.setObjectName("objCrumbBar")
        self._crumb_lay = QHBoxLayout(self._crumb_bar)
        self._crumb_lay.setContentsMargins(12, 4, 12, 4)
        self._crumb_lay.setSpacing(2)
        self._crumb_bar.hide()
        root.addWidget(self._crumb_bar)

        # Type badge + short SHA + size
        self._meta_bar = QWidget()
        self._meta_bar.setStyleSheet(f"background:{BG_PANEL};")
        ml = QHBoxLayout(self._meta_bar)
        ml.setContentsMargins(12, 5, 12, 5)
        ml.setSpacing(10)

        self._type_badge = QLabel()
        self._type_badge.setStyleSheet(
            "font-size:10px; font-weight:700; border-radius:3px;"
            " padding:1px 6px; color:white;"
        )
        self._meta_info = label("", 11, TEXT_TERTIARY)

        ml.addWidget(self._type_badge)
        ml.addWidget(self._meta_info)
        ml.addStretch()
        self._meta_bar.hide()
        root.addWidget(self._meta_bar)
        root.addWidget(h_separator())

        self._stack = QStackedWidget()

        self._stack.addWidget(_placeholder_tab("⬡", "Object Explorer", "Type or paste a SHA above and press Enter"))
        self._blob_r = BlobRenderer();   self._stack.addWidget(self._blob_r)
        self._tree_r = TreeRenderer();   self._stack.addWidget(self._tree_r)
        self._commit_r = CommitRenderer(); self._stack.addWidget(self._commit_r)
        self._tag_r = TagRenderer();    self._stack.addWidget(self._tag_r)

        # Wire SHA links
        for renderer in (self._tree_r, self._commit_r, self._tag_r):
            renderer.sha_clicked.connect(self._navigate)

        root.addWidget(self._stack)
        state.repo_changed.connect(self._on_repo_changed)


    # Slots
    def _on_repo_changed(self, _repo):
        """Reset to empty state when repo switches."""
        self._history.clear()
        self._sha_input.clear()
        self._stack.setCurrentIndex(self._PAGE_EMPTY)
        self._meta_bar.hide()
        self._crumb_bar.hide()
        self._back_btn.setEnabled(False)


    def _lookup(self):
        sha = self._sha_input.text().strip()
        if sha:
            self._navigate(sha)


    def _navigate(self, sha: str):
        """Push sha onto the history stack and render it."""
        self._history.append(sha)
        self._sha_input.setText(sha)
        self._back_btn.setEnabled(len(self._history) > 1)
        if not self._render(sha):
            self._history.pop()
            self._back_btn.setEnabled(len(self._history) > 1)
        self._rebuild_crumbs()


    def _go_back(self):
        if len(self._history) > 1:
            self._history.pop()
            sha = self._history[-1]
            self._sha_input.setText(sha)
            self._back_btn.setEnabled(len(self._history) > 1)
            self._render(sha)
            self._rebuild_crumbs()


    def _jump_to(self, index: int):
        """Navigate directly to a breadcrumb index (prunes forward history)."""
        self._history = self._history[: index + 1]
        sha = self._history[-1]
        self._sha_input.setText(sha)
        self._back_btn.setEnabled(len(self._history) > 1)
        self._render(sha)
        self._rebuild_crumbs()


    # Core render pipeline
    def _render(self, sha: str) -> bool:
        repo = self._state.repo
        if repo is None:
            self._flash_error("No repository loaded.")
            return False
        try:
            obj = repo.rev_parse(sha)
        except Exception as exc:
            self._flash_error(f'Cannot resolve "{sha[:16]}": {exc}')
            self._state.logger.log(f"Object lookup failed: {sha} — {exc}", "ERR ")
            return False

        self._update_meta(obj)
        self._state.logger.log(
            f"Object Explorer: {obj.type}  {obj.hexsha[:12]}"
            + (f"  {obj.size} bytes" if hasattr(obj, "size") else "")
        )

        dispatch = {
            "blob":   (self._PAGE_BLOB,   lambda: self._blob_r.show_blob(obj)),
            "tree":   (self._PAGE_TREE,   lambda: self._tree_r.show_tree(obj)),
            "commit": (self._PAGE_COMMIT, lambda: self._commit_r.show_commit(obj)),
            "tag":    (self._PAGE_TAG,    lambda: self._tag_r.show_tag(obj)),
        }
        page, populate = dispatch.get(
            obj.type, (self._PAGE_EMPTY, lambda: None)
        )
        populate()
        self._stack.setCurrentIndex(page)
        return True


    def _update_meta(self, obj):
        color = self._TYPE_COLORS.get(obj.type, TEXT_TERTIARY)
        self._type_badge.setText(obj.type.upper())
        self._type_badge.setStyleSheet(
            f"color:white; background:{color}; border-radius:3px;"
            " font-size:10px; font-weight:700; padding:1px 6px;"
        )
        size_part = f"  ·  {obj.size} bytes" if hasattr(obj, "size") else ""
        self._meta_info.setText(f"{obj.hexsha[:20]}{size_part}")
        self._meta_bar.show()


    def _flash_error(self, msg: str):
        self._type_badge.setText("ERR")
        self._type_badge.setStyleSheet(
            f"color:white; background:{ACCENT_RED}; border-radius:3px;"
            " font-size:10px; font-weight:700; padding:1px 6px;"
        )
        self._meta_info.setText(msg)
        self._meta_bar.show()
        self._stack.setCurrentIndex(self._PAGE_EMPTY)



    def _rebuild_crumbs(self):
        while self._crumb_lay.count():
            item = self._crumb_lay.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()


        if not self._history:
            self._crumb_bar.hide()
            return

        self._crumb_bar.show()
        for i, sha in enumerate(self._history):
            is_current = (i == len(self._history) - 1)
            short = sha[:10]

            if is_current:
                w = label(short, 11, TEXT_PRIMARY, 600)
            else:
                w = QPushButton(short)
                w.setObjectName("objCrumb")
                w.setFlat(True)
                w.setStyleSheet(
                    f"color:{ACCENT}; font-size:11px; background:transparent;"
                    " border:none; padding:0 2px;"
                )
                w.clicked.connect(
                    lambda checked=False, idx=i: self._jump_to(idx)
                )

            self._crumb_lay.addWidget(w)

            if not is_current:
                self._crumb_lay.addWidget(label("›", 11, TEXT_TERTIARY))

        self._crumb_lay.addStretch()



def _placeholder_tab(icon: str, title: str, subtitle: str) -> QWidget:

    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.setSpacing(6)

    # Large glyph/icon
    icon_lbl = QLabel(icon)
    icon_lbl.setStyleSheet("font-size: 32px; color: TEXT_TERTIARY;")
    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    # Main title
    title_lbl = QLabel(title)
    title_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: TEXT_PRIMARY;")
    title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    # Subtitle description
    sub_lbl = QLabel(subtitle)
    sub_lbl.setStyleSheet("font-size: 12px; color: TEXT_TERTIARY;")
    sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    layout.addWidget(icon_lbl)
    layout.addWidget(title_lbl)
    layout.addWidget(sub_lbl)
    
    return widget