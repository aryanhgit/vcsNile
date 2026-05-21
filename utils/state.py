"""
Legacy import shim.

AppState now lives in git_backend/state.py so shared application state does not
depend on widget modules.
"""

from git_backend.state import AppState
