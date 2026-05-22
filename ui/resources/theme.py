from ui.resources.constants import *

STYLESHEET = f"""
QMainWindow, QWidget {{
    background: {BG_BASE};
    color: {TEXT_PRIMARY};
    font-family: "SF Pro Text", "Segoe UI", "Noto Sans", sans-serif;
    font-size: 13px;
}}

/* ── Toolbar ── */
QToolBar {{
    background: {BG_PANEL};
    border-bottom: 1px solid {SEPARATOR};
    spacing: 6px;
    padding: 4px 8px;
}}
QToolBar QPushButton {{
    background: transparent;
    border: none;
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 5px 10px;
    font-size: 13px;
}}
QToolBar QPushButton:hover {{
    background: {BG_HOVER};
}}
QToolBar QPushButton:pressed {{
    background: {SEPARATOR};
}}



/* ── Menu bar ── */
QMenuBar {{
    background: {BG_PANEL};
    border-bottom: 1px solid {SEPARATOR};
    padding: 2px 4px;
}}
QMenuBar::item {{ background: transparent; padding: 4px 10px; border-radius: 5px; }}
QMenuBar::item:selected {{ background: {BG_HOVER}; }}

QMenu {{
    background: {BG_PANEL};
    border: 1px solid {SEPARATOR};
    border-radius: 8px;
    padding: 4px 0;
}}
QMenu::item {{
    padding: 6px 28px 6px 16px;
    border-radius: 4px;
    margin: 1px 4px;
}}
QMenu::item:selected {{ background: {ACCENT}; color: white; }}
QMenu::item:disabled {{ color: {TEXT_TERTIARY}; }}
QMenu::separator  {{ height: 1px; background: {SEPARATOR}; margin: 4px 10px; }}



/* ── Sidebar ── */
#sidebar {{
    background: {BG_PANEL};
    border-right: 1px solid {SEPARATOR};
}}
#sidebar QTreeWidget {{
    background: transparent;
    border: none;
    outline: none;
    padding: 4px 0;
}}
#sidebar QTreeWidget::item {{
    height: 28px;
    padding-left: 8px;
    border-radius: 6px;
    color: {TEXT_PRIMARY};
}}
#sidebar QTreeWidget::item:hover {{
    background: {BG_HOVER};
}}
#sidebar QTreeWidget::item:selected {{
    background: {ACCENT};
    color: white;
}}
#sidebar QTreeWidget::branch {{
    background: transparent;
}}


/* ── Section headers inside sidebar ── */
#sectionLabel {{
    color: {TEXT_TERTIARY};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.6px;
    padding: 14px 14px 4px 14px;
    text-transform: uppercase;
}}


/* ── Tabs ── */
QTabWidget::pane {{
    border: none;
    background: {BG_BASE};
}}
QTabBar {{
    background: {BG_PANEL};
    border-bottom: 1px solid {SEPARATOR};
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_SECONDARY};
    padding: 8px 18px;
    font-size: 13px;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
}}
QTabBar::tab:hover {{
    color: {TEXT_PRIMARY};
}}
QTabBar::tab:selected {{
    color: {TEXT_PRIMARY};
    border-bottom: 2px solid {ACCENT};
    font-weight: 500;
}}


/* ── Details panel ── */
#detailsPanel {{
    background: {BG_PANEL};
    border-left: 1px solid {SEPARATOR};
}}


/* ── Placeholder canvas areas ── */
#canvas {{
    background: {BG_BASE};
    border: 1.5px dashed {SEPARATOR};
    border-radius: 10px;
    color: {TEXT_TERTIARY};
}}


/* ── Commit list items ── */
QListWidget {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget::item {{
    border-radius: 6px;
    padding: 4px 8px;
    color: {TEXT_PRIMARY};
}}
QListWidget::item:hover {{
    background: {BG_HOVER};
}}
QListWidget::item:selected {{
    background: {ACCENT};
    color: white;
}}


/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
}}
QScrollBar::handle:vertical {{
    background: {BG_HOVER};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
}}
QScrollBar::handle:horizontal {{
    background: {BG_HOVER};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}



/* ── QSplitter handle ── */
QSplitter::handle {{
    background: {SEPARATOR};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}



/* ── Text edit ── */
QTextEdit {{
    background: transparent;
    border: none;
    color: {TEXT_SECONDARY};
    font-size: 12px;
    line-height: 1.6;
    padding: 8px;
}}


/* ── Sidebar grouped tree ── */
#sidebarTree {{
    background: transparent; border: none; outline: none;
}}
#sidebarTree::item {{
    height: 26px; border-radius: 5px; padding-left: 2px;
}}
#sidebarTree::item:hover    {{ background: {BG_HOVER}; }}
#sidebarTree::item:selected {{ background: {ACCENT}; color: white; }}
/* collapse/expand arrow — tinted to match palette */
#sidebarTree::branch {{ background: transparent; }}
#sidebarTree::branch:has-children:closed {{ color: {TEXT_TERTIARY}; }}
#sidebarTree::branch:open               {{ color: {TEXT_SECONDARY}; }}

/* ── Status bar ── */
QStatusBar {{
    background: {BG_PANEL};
    color: {TEXT_TERTIARY};
    border-top: 1px solid {SEPARATOR};
    font-size: 12px;
    padding: 0 8px;
}}


/* ── Log panel ── */
#logPanel  {{ background: {BG_PANEL}; border-top: 1px solid {SEPARATOR}; }}
#logHeader {{ background: {BG_PANEL}; border-bottom: 1px solid {SEPARATOR}; }}
#logToggle {{
    background: transparent; border: none; border-radius: 4px;
    color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 500;
    padding: 0 6px; text-align: left; min-width: 80px;
}}
#logToggle:hover  {{ color: {TEXT_PRIMARY}; background: {BG_HOVER}; }}
#logClear {{
    background: {BG_HOVER}; border: none; border-radius: 4px;
    color: {TEXT_TERTIARY}; font-size: 11px; padding: 1px 8px;
}}
#logClear:hover  {{ color: {TEXT_PRIMARY}; background: {SEPARATOR}; }}
#logOutput {{
    background: {BG_BASE}; border: none; outline: none;
    color: {TEXT_SECONDARY};
    font-family: "SF Mono", "Menlo", "Consolas", monospace;
    font-size: 11px; padding: 6px 10px;
    selection-background-color: {ACCENT};
}}



/* ── Status bar ── */
QStatusBar {{
    background: {BG_PANEL}; color: {TEXT_TERTIARY};
    border-top: 1px solid {SEPARATOR}; font-size: 12px; padding: 0 8px;
}}



/* ── Staging columns ── */
#stagingColumn     {{ background: {BG_PANEL}; }}
#stagingColHeader  {{ background: {BG_PANEL}; }}
#stagingList {{
    background: {BG_BASE}; border: none; outline: none;
}}
#stagingList::item {{
    border-radius: 5px; padding: 0;
}}
#stagingList::item:hover    {{ background: {BG_HOVER}; }}
#stagingList::item:selected {{ background: {ACCENT}; }}
#stagingAction {{
    background: {BG_HOVER}; border: none; border-radius: 4px;
    font-size: 11px; padding: 0 8px;
}}
#stagingAction:hover {{ background: {SEPARATOR}; color: {TEXT_PRIMARY}; }}


/* ── Object Explorer ── */
#objInputBar {{
    background: {BG_PANEL}; border-bottom: 1px solid {SEPARATOR};
}}
#objShaInput {{
    background: {BG_BASE}; border: 1px solid {SEPARATOR}; border-radius: 6px;
    color: {TEXT_PRIMARY}; font-family: "SF Mono","Menlo","Consolas",monospace;
    font-size: 12px; padding: 4px 10px; selection-background-color: {ACCENT};
}}
#objShaInput:focus {{ border-color: {ACCENT}; }}
#objLookupBtn, #objBackBtn {{
    background: {BG_HOVER}; border: none; border-radius: 6px;
    color: {TEXT_PRIMARY}; font-size: 12px; padding: 0 12px;
}}
#objLookupBtn:hover {{ background: {ACCENT}; color: white; }}
#objBackBtn:hover   {{ background: {BG_HOVER}; color: {TEXT_PRIMARY}; }}
#objBackBtn:disabled {{ color: {TEXT_TERTIARY}; }}
#objCrumbBar {{ background: {BG_PANEL}; border-bottom: 1px solid {SEPARATOR}; }}
#objTreeView {{
    background: {BG_BASE}; border: none; outline: none;
    alternate-background-color: {BG_HOVER};
}}
#objTreeView::item:hover    {{ background: {BG_HOVER}; }}
#objTreeView::item:selected {{ background: {ACCENT}; color: white; }}
#objTreeView QHeaderView::section {{
    background: {BG_PANEL}; color: {TEXT_TERTIARY}; font-size: 11px;
    font-weight: 600; padding: 4px 8px; border: none;
    border-bottom: 1px solid {SEPARATOR};
}}
#objBlobEditor, #objCommitMsg, #objTagMsg {{
    background: {BG_BASE}; border: none; outline: none;
    color: {TEXT_SECONDARY};
    font-family: "SF Mono","Menlo","Consolas",monospace;
    font-size: 12px; padding: 8px 12px;
    selection-background-color: {ACCENT};
}}
"""