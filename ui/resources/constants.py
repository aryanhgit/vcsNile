BG_BASE = "#1C1C1E"
BG_PANEL = "#2C2C2E"
BG_HOVER = "#3A3A3C"
SEPARATOR = "#3A3A3C"
ACCENT = "#0A84FF"
ACCENT_GREEN = "#30D158"
ACCENT_RED = "#FF453A"
ACCENT_ORANGE = "#FF9F0A"
TEXT_PRIMARY = "#F2F2F7"
TEXT_SECONDARY = "#8E8E93"
TEXT_TERTIARY = "#636366"

MAX_RECENT = 8


# Status char : (badge glyph, badge colour, tooltip label)
STATUS_META: dict[str, tuple[str, str, str]] = {
    "M": ("M", ACCENT_ORANGE, "modified"),
    "A": ("+", ACCENT_GREEN, "added"),
    "D": ("−", ACCENT_RED, "deleted"),
    "R": ("R", ACCENT, "renamed"),
    "?": ("+", ACCENT_GREEN, "untracked"),
    "C": ("·", TEXT_TERTIARY, "committed"),
}