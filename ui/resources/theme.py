from ui.resources.constants import (BG_BASE, BG_PANEL, BG_HOVER, SEPARATOR, ACCENT, ACCENT_GREEN, ACCENT_RED, 
                                    ACCENT_ORANGE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY)
STYLESHEET = f"""
QMainWindow, QWidget {{
    background: {BG_BASE};
    color: {TEXT_PRIMARY};
    font-family: "SF Pro Text", "Segoe UI", "Noto Sans", sans-serif;
    font-size: 13px;
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



/* ── Time Travel panel ── */
#ttCard {{
    background: {BG_PANEL};
    border: 1px solid {SEPARATOR};
    border-radius: 10px;
}}
#ttDesc {{
    color: {TEXT_SECONDARY}; font-size: 12px; background: transparent;
}}
#ttInput {{
    background: {BG_BASE}; border: 1px solid {SEPARATOR}; border-radius: 6px;
    color: {TEXT_PRIMARY}; font-size: 12px; padding: 5px 10px; min-height: 28px;
    selection-background-color: {ACCENT};
}}
#ttInput:focus {{ border-color: {ACCENT}; }}
#ttCombo {{
    background: {BG_BASE}; border: 1px solid {SEPARATOR}; border-radius: 6px;
    color: {TEXT_PRIMARY}; font-size: 12px; padding: 3px 8px; min-height: 28px;
}}
#ttCombo QAbstractItemView {{
    background: {BG_PANEL}; border: 1px solid {SEPARATOR};
    selection-background-color: {ACCENT}; color: {TEXT_PRIMARY};
}}
#ttWarning {{ color: {ACCENT_ORANGE}; font-size: 11px; background: transparent; }}
#ttResultArea {{
    background: {BG_BASE}; border: none; outline: none;
    color: {TEXT_SECONDARY};
    font-family: "SF Mono","Menlo","Consolas",monospace;
    font-size: 11px; padding: 6px 10px;
}}
QRadioButton {{
    color: {TEXT_PRIMARY}; font-size: 12px; background: transparent; spacing: 6px;
}}
QRadioButton::indicator {{ width: 14px; height: 14px; }}
QCheckBox {{
    color: {TEXT_PRIMARY}; font-size: 12px; background: transparent; spacing: 6px;
}}
QCheckBox::indicator {{
    width: 14px; height: 14px; border-radius: 3px; border: 1px solid {SEPARATOR};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}




/* ── DAG Canvas ── */
#dagCanvas {{
    background: {BG_BASE}; border: none; outline: none;
}}
#dagCheckoutBtn {{
    background: {ACCENT_GREEN}; border: none; border-radius: 5px;
    color: white; font-size: 11px; font-weight: 600;
    padding: 0 12px;
}}
#dagCheckoutBtn:hover   {{ background: #27bd4e; }}
#dagCheckoutBtn:pressed {{ background: #1a9e40; }}
#dagEmptyHint {{
    color: {TEXT_TERTIARY}; font-size: 13px; background: transparent;
}}




/* ── Reset visualizer ── */
#resetDagPreview {{
    background: {BG_BASE}; border: 1px solid {SEPARATOR};
    border-radius: 8px;
}}
#resetDiagram {{ background: transparent; }}
#resetConfirmBtn {{
    background: {ACCENT_RED}; border: none; border-radius: 6px;
    color: white; font-size: 12px; font-weight: 600; padding: 0 16px;
}}
#resetConfirmBtn:hover   {{ background: #e03328; }}
#resetConfirmBtn:pressed {{ background: #bf2a22; }}
#resetWarnBox {{
    background: rgba(255,69,58,0.12);
    border: 1px solid {ACCENT_RED};
    border-radius: 6px;
}}
#resetSummaryLabel {{ font-size: 12px; font-weight: 500; background: transparent; }}
#resetCancelBtn {{
    background: {BG_HOVER}; border: none; border-radius: 6px;
    color: {TEXT_PRIMARY}; font-size: 12px; padding: 0 16px;
}}
#resetCancelBtn:hover {{ background: {SEPARATOR}; }}

#rvTargetInput {{
    background: {BG_BASE}; border: 1px solid {SEPARATOR}; border-radius: 6px;
    color: {TEXT_PRIMARY}; font-family: "SF Mono","Menlo",monospace;
    font-size: 12px; padding: 5px 10px; min-height: 28px;
    selection-background-color: {ACCENT};
}}
#rvTargetInput:focus {{ border-color: {ACCENT}; }}
#rvPreviewBtn {{
    background: {BG_HOVER}; border: none; border-radius: 6px;
    color: {TEXT_PRIMARY}; font-size: 12px; padding: 0 14px; min-height: 28px;
}}
#rvPreviewBtn:hover {{ background: {ACCENT}; color: white; }}
#rvConfirmBtn {{
    background: {ACCENT_RED}; border: none; border-radius: 6px;
    color: white; font-size: 13px; font-weight: 600; padding: 0 20px; min-height: 36px;
}}
#rvConfirmBtn:hover    {{ background: #d93c33; }}
#rvConfirmBtn:disabled {{ background: {BG_HOVER}; color: {TEXT_TERTIARY}; }}
#rvWarning {{ color: {ACCENT_ORANGE}; font-size: 11px; background: transparent; }}
#rvModeCard {{
    background: {BG_PANEL}; border-radius: 8px; border: 1px solid {SEPARATOR};
}}



/* ── Merge Conflict Visualizer ── */
#conflictPane {{ background: {BG_PANEL}; }}
#conflictEditor {{
    background: {BG_BASE}; border: none; outline: none;
    color: {TEXT_PRIMARY};
    font-family: "SF Mono","Menlo","Consolas",monospace;
    font-size: 11px; padding: 4px 8px;
    selection-background-color: {ACCENT};
}}
/* Thin coloured left border on each pane to orient the user */
#conflictPane[role="ours"]    {{ border-left: 3px solid {ACCENT}; }}
#conflictPane[role="theirs"]  {{ border-left: 3px solid {ACCENT_ORANGE}; }}
#conflictPane[role="base"]    {{ border-left: 3px solid {TEXT_TERTIARY}; }}
/* Legend pills */
#legendPill {{
    background: {BG_BASE}; border-radius: 3px; padding: 1px 5px;
    font-size: 10px;
}}



/* ── Command Preview Panel ── */
#cmdPanel {{ background: {BG_PANEL}; border-top: 1px solid {SEPARATOR}; }}
#cmdBar   {{ background: {BG_PANEL}; }}
#cmdInput {{
    background: {BG_BASE}; border: 1px solid {SEPARATOR}; border-radius: 6px;
    color: {TEXT_PRIMARY};
    font-family: "SF Mono","Menlo","Consolas",monospace;
    font-size: 12px; padding: 4px 10px;
    selection-background-color: {ACCENT};
}}
#cmdInput:focus {{ border-color: {ACCENT}; }}
#cmdPreviewBtn {{
    background: {ACCENT}; border: none; border-radius: 5px;
    color: white; font-size: 11px; font-weight: 600; padding: 0 12px;
}}
#cmdPreviewBtn:hover  {{ background: #0077e6; }}
#cmdToggleBtn {{
    background: {BG_HOVER}; border: none; border-radius: 5px;
    color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 700;
}}
#cmdToggleBtn:hover {{ color: {TEXT_PRIMARY}; background: {SEPARATOR}; }}
#cmdTree {{
    background: {BG_BASE}; border: none; outline: none; font-size: 12px;
}}
#cmdTree::item           {{ padding: 3px 2px; }}
#cmdTree::item:hover     {{ background: {BG_HOVER}; }}
#cmdTree::item:selected  {{ background: {ACCENT}; color: white; }}



/* ── Reflog tree ── */
#reflogTree {{
    background: {BG_BASE};
    border: none;
    outline: none;
}}
#reflogTree::item {{
    height: 26px;
    padding-left: 6px;
    border-radius: 4px;
}}
#reflogTree::item:hover    {{ background: {BG_HOVER}; }}
#reflogTree::item:selected {{ background: {ACCENT}; color: white; }}


/* ── Diff panel ── */
QPlainTextEdit#diffEditor {{
    background: {BG_BASE};
    color: {TEXT_SECONDARY};
    border: none;
    selection-background-color: {BG_HOVER};
    selection-color: {TEXT_PRIMARY};
}}
"""