from PySide6.QtWidgets import (QLabel, QFrame)
from ui.resources.constants import *

def label(text: str, size=13, color=TEXT_PRIMARY, weight=400) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {color}; font-size: {size}px; font-weight: {weight};"
        " background: transparent; border: none;"
    )
    return lbl


def section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("sectionLabel")
    lbl.setStyleSheet(
        f"color: {TEXT_TERTIARY}; font-size: 11px; font-weight: 600;"
        f" letter-spacing: 0.6px; padding: 14px 14px 4px 14px;"
        " background: transparent;"
    )
    return lbl


def h_separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {SEPARATOR}; background: {SEPARATOR}; max-height: 1px;")
    return line


def dot_badge(color: str, size=8) -> QLabel:
    lbl = QLabel()
    lbl.setFixedSize(size, size)
    lbl.setStyleSheet(f"background: {color}; border-radius: {size//2}px;")
    return lbl
