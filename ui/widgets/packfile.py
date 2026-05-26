import os
import struct

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QPushButton,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui  import QColor, QFont

from ui.resources.theme import (
    BG_PANEL, BG_HOVER, SEPARATOR,
    ACCENT, ACCENT_GREEN, ACCENT_RED, ACCENT_ORANGE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
)
from utils.helper import label


try:
    import pygit2
    PYGIT2_OK = True
except ImportError:
    PYGIT2_OK = False

_IDX_MAGIC   = b"\xff\x74\x4f\x63"
_FAN_ENTRIES = 256
_SHA_LEN     = 20

_TYPE = {1: "commit", 2: "tree", 3: "blob", 4: "tag",
         6: "ofs_delta", 7: "ref_delta"}

_TYPE_COLOR = {
    "commit":    ACCENT_ORANGE,
    "tree":      ACCENT,
    "blob":      ACCENT_GREEN,
    "tag":       ACCENT_RED,
    "ofs_delta": TEXT_SECONDARY,
    "ref_delta": TEXT_SECONDARY,
}

_C_SHA, _C_TYPE, _C_SIZE, _C_COMP, _C_PACK = 0, 1, 2, 3, 4


class _PackIndexReader:
    @staticmethod
    def read(idx_path: str) -> list[tuple[str, int]]:
        with open(idx_path, "rb") as fh:
            data = fh.read()

        if data[:4] != _IDX_MAGIC:
            return []
        if struct.unpack_from(">I", data, 4)[0] != 2:
            return []

        fan_off = 8
        n       = struct.unpack_from(">I", data, fan_off + (_FAN_ENTRIES - 1) * 4)[0]

        sha_off  = fan_off + _FAN_ENTRIES * 4
        crc_off  = sha_off  + n * _SHA_LEN
        off_off  = crc_off  + n * 4
        loff_off = off_off  + n * 4

        entries = []
        for i in range(n):
            sha     = data[sha_off + i * _SHA_LEN : sha_off + (i + 1) * _SHA_LEN].hex()
            raw_off = struct.unpack_from(">I", data, off_off + i * 4)[0]
            if raw_off & 0x80000000:
                raw_off = struct.unpack_from(">Q", data, loff_off + (raw_off & 0x7FFFFFFF) * 8)[0]
            entries.append((sha, raw_off))

        return entries


class PackfileTab(QWidget):
    def __init__(self, state):
        super().__init__()
        self._state        = state
        self._rows: list   = []
        self._filter_timer = QTimer()
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(200)
        self._filter_timer.timeout.connect(self._apply_filter)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        banner = QWidget()
        banner.setStyleSheet(f"background:{BG_PANEL}; border-bottom:1px solid {SEPARATOR};")
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(16, 10, 16, 10)
        note = QLabel(
            "Git packs loose objects into binary packfiles to save space and speed up "
            "transfers. Each .pack has a companion .idx index. Inspect every packed object — "
            "its type, decoded size, and compressed size on disk."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:12px; background:transparent;")
        bl.addWidget(note, 1)
        root.addWidget(banner)

        # ── Toolbar ───────────────────────────────────────────────────────────
        bar = QWidget()
        bar.setStyleSheet(f"background:{BG_PANEL}; border-bottom:1px solid {SEPARATOR};")
        bl2 = QHBoxLayout(bar)
        bl2.setContentsMargins(12, 7, 12, 7)
        bl2.setSpacing(8)

        self._filter_input = QLineEdit()
        self._filter_input.setObjectName("packFilter")
        self._filter_input.setPlaceholderText("Filter by SHA or type…")
        self._filter_input.textChanged.connect(lambda _: self._filter_timer.start())
        bl2.addWidget(self._filter_input, 1)

        self._stat_lbl = label("", 11, TEXT_TERTIARY)
        bl2.addWidget(self._stat_lbl)

        self._refresh_btn = QPushButton("↺  Reload")
        self._refresh_btn.setStyleSheet(
            f"background:{BG_HOVER}; border:none; border-radius:5px;"
            f"color:{TEXT_PRIMARY}; font-size:12px; padding:4px 10px;"
        )
        self._refresh_btn.clicked.connect(self._load)
        bl2.addWidget(self._refresh_btn)
        root.addWidget(bar)

        # ── No-pygit2 notice ──────────────────────────────────────────────────
        self._no_pg = QWidget()
        npl = QVBoxLayout(self._no_pg)
        npl.setAlignment(Qt.AlignCenter)
        npl.addWidget(label("pygit2 is not installed", 15, TEXT_TERTIARY, 500))
        npl.addSpacing(4)
        npl.addWidget(label("pip install pygit2", 13, ACCENT))
        self._no_pg.setVisible(False)
        root.addWidget(self._no_pg)

        # ── Table ─────────────────────────────────────────────────────────────
        self._table = QTableWidget(0, 5)
        self._table.setObjectName("packTable")
        self._table.setHorizontalHeaderLabels(["SHA", "Type", "Decoded", "Compressed", "Pack"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(True)

        hdr = self._table.horizontalHeader()
        for col, width, mode in [
            (_C_SHA,  82, QHeaderView.Fixed),
            (_C_TYPE, 76, QHeaderView.Fixed),
            (_C_SIZE, 80, QHeaderView.Fixed),
            (_C_COMP, 90, QHeaderView.Fixed),
            (_C_PACK,  0, QHeaderView.Stretch),
        ]:
            hdr.setSectionResizeMode(col, mode)
            if mode == QHeaderView.Fixed:
                self._table.setColumnWidth(col, width)

        root.addWidget(self._table)

        state.repo_changed.connect(self._on_repo_changed)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_repo_changed(self, repo):
        self._table.setRowCount(0)
        self._rows.clear()
        self._stat_lbl.setText("")
        if repo is not None:
            self._load()

    def _load(self):
        repo = self._state.repo
        if repo is None:
            return

        if not PYGIT2_OK:
            self._table.setVisible(False)
            self._no_pg.setVisible(True)
            return

        self._table.setVisible(True)
        self._no_pg.setVisible(False)

        pack_dir = os.path.join(repo.working_dir, ".git", "objects", "pack")
        if not os.path.isdir(pack_dir):
            self._stat_lbl.setText("No packfiles found")
            return

        idx_files = [
            os.path.join(pack_dir, f)
            for f in os.listdir(pack_dir) if f.endswith(".idx")
        ]
        if not idx_files:
            self._stat_lbl.setText("No .idx files found")
            return

        try:
            pg_repo = pygit2.Repository(repo.working_dir)
        except Exception as exc:
            self._stat_lbl.setText(f"pygit2 error: {exc}")
            return

        self._rows.clear()

        for idx_path in sorted(idx_files):
            pack_name  = os.path.basename(idx_path).replace(".idx", "")
            pack_path  = idx_path[:-4] + ".pack"
            pack_size  = os.path.getsize(pack_path) if os.path.exists(pack_path) else 0
            entries    = _PackIndexReader.read(idx_path)
            if not entries:
                continue

            sorted_entries = sorted(entries, key=lambda e: e[1])
            offsets        = [off for _, off in sorted_entries]
            pack_data_end  = max(pack_size - 20, 0)

            for i, (sha, offset) in enumerate(sorted_entries):
                next_off  = offsets[i + 1] if i + 1 < len(offsets) else pack_data_end
                comp_size = max(0, next_off - offset)

                try:
                    raw_obj   = pg_repo.odb.read(pygit2.Oid(hex=sha))
                    type_name = _TYPE.get(raw_obj.type, f"type_{raw_obj.type}")
                    dec_size  = len(raw_obj.data)
                except Exception:
                    type_name = "?"
                    dec_size  = 0

                self._rows.append((sha, type_name, dec_size, comp_size, pack_name))

        self._table.setSortingEnabled(False)
        self._populate_table(self._rows)
        self._table.setSortingEnabled(True)
        self._update_stats(len(self._rows))

    def _populate_table(self, rows: list):
        self._table.setRowCount(0)
        mono = QFont()
        mono.setFamilies(["SF Mono", "Menlo", "Consolas"])
        mono.setPointSize(11)

        for sha, type_name, dec_size, comp_size, pack_name in rows:
            r = self._table.rowCount()
            self._table.insertRow(r)

            sha_item = QTableWidgetItem(sha[:8])
            sha_item.setFont(mono)
            sha_item.setForeground(QColor(ACCENT))
            sha_item.setToolTip(sha)
            sha_item.setData(Qt.UserRole, sha)

            type_item = QTableWidgetItem(type_name)
            type_item.setForeground(QColor(_TYPE_COLOR.get(type_name, TEXT_SECONDARY)))

            dec_item = _SizeItem(dec_size)
            dec_item.setForeground(QColor(TEXT_PRIMARY))
            dec_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            comp_item = _SizeItem(comp_size)
            comp_item.setForeground(QColor(ACCENT_GREEN if comp_size < dec_size else ACCENT_RED))
            comp_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            short     = pack_name[5:17] + "…" if len(pack_name) > 18 else pack_name
            pack_item = QTableWidgetItem(short)
            pack_item.setForeground(QColor(TEXT_TERTIARY))
            pack_item.setToolTip(pack_name)

            for col, item in enumerate([sha_item, type_item, dec_item, comp_item, pack_item]):
                self._table.setItem(r, col, item)
            self._table.setRowHeight(r, 24)

    def _apply_filter(self):
        text     = self._filter_input.text().strip().lower()
        filtered = self._rows if not text else [
            row for row in self._rows
            if text in row[0].lower() or text in row[1].lower()
        ]
        self._table.setSortingEnabled(False)
        self._populate_table(filtered)
        self._table.setSortingEnabled(True)
        self._update_stats(len(filtered), len(self._rows))

    def _update_stats(self, shown: int, total: int | None = None):
        if total is None or shown == total:
            total_dec  = sum(r[2] for r in self._rows)
            total_comp = sum(r[3] for r in self._rows)
            ratio      = total_comp / max(total_dec, 1) * 100
            self._stat_lbl.setText(
                f"{shown} objects  ·  "
                f"{_fmt_size(total_dec)} decoded  ·  "
                f"{_fmt_size(total_comp)} packed  ·  "
                f"{ratio:.0f}% ratio"
            )
        else:
            self._stat_lbl.setText(f"{shown} / {total} objects")


class _SizeItem(QTableWidgetItem):
    def __init__(self, size: int):
        super().__init__(_fmt_size(size))
        self._size = size

    def __lt__(self, other: "_SizeItem") -> bool:
        if isinstance(other, _SizeItem):
            return self._size < other._size
        return super().__lt__(other)


def _fmt_size(n: int) -> str:
    if n < 1024:        return f"{n} B"
    if n < 1024 ** 2:  return f"{n / 1024:.1f} KB"
    return f"{n / 1024 ** 2:.2f} MB"