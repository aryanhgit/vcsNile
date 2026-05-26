import os
import sys
import shlex, hashlib, time

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QTreeWidgetItem, QTreeWidget
)

from ui.resources.constants import (ACCENT, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED, BG_BASE, 
                                    BG_PANEL, SEPARATOR, TEXT_PRIMARY, TEXT_TERTIARY, TEXT_SECONDARY)
from utils.state import AppState

# ─────────────────────────────────────────────────────────────────────────────
# Command ↔ Internal Changes Panel  (Phase 4.6)
# ─────────────────────────────────────────────────────────────────────────────

class GitCommandParser:
    """
    Parses 'git <verb> [flags] [args]' into a structured dict.

    Uses shlex so quoted strings ("fix login bug") are handled correctly.
    The leading 'git' token is optional — the user may omit it.

    Returns
    -------
    {
      "original": str,      # full input as typed
      "verb":     str,      # e.g. "commit"
      "flags":    dict,     # {"-m": "fix", "--amend": True, …}
      "args":     list,     # positional arguments
      "known":    bool,     # True when verb is in SUPPORTED
    }
    Returns None on parse failure (e.g. unclosed quote).
    """

    SUPPORTED = {
        "commit":   "Create a new commit from staged changes",
        "add":      "Stage file(s) to the index",
        "checkout": "Move HEAD to a ref or restore files",
        "switch":   "Move HEAD to a branch (modern syntax)",
        "reset":    "Move branch tip and optionally index / WD",
        "branch":   "Create, list, or delete a branch",
        "tag":      "Create a lightweight or annotated tag",
        "revert":   "Create an inverse commit to undo changes",
        "merge":    "Merge a branch into the current branch",
        "stash":    "Save and restore dirty working-directory state",
    }

    @classmethod
    def parse(cls, raw: str) -> "dict | None":
        try:
            tokens = shlex.split(raw.strip())
        except ValueError:
            return None

        if not tokens:
            return None
        if tokens[0].lower() == "git":
            tokens = tokens[1:]
        if not tokens:
            return None

        verb = tokens[0].lower()
        flags, args, i = {}, [], 1

        while i < len(tokens):
            t = tokens[i]
            if t.startswith("-"):
                nxt_is_val = (i + 1 < len(tokens) and not tokens[i+1].startswith("-"))
                if nxt_is_val:
                    flags[t] = tokens[i+1]; i += 2
                else:
                    flags[t] = True; i += 1
            else:
                args.append(t); i += 1

        return {"original": raw.strip(), "verb": verb,
                "flags": flags, "args": args, "known": verb in cls.SUPPORTED}


class GitCommandPredictor:
    """
    Predicts what internal git changes a command would produce,
    based entirely on the current repository state.

    COMPLETELY READ-ONLY — no git operations are performed.

    Each verb handler returns a prediction dict:
    {
      "command":        str,   # original input
      "verb":           str,
      "supported":      bool,
      "interpretation": str,   # plain-English summary
      "objects":        list,  # [{type, action, name, sha_before, sha_after, detail}]
      "refs":           list,  # [{type, action, name, sha_before, sha_after, detail}]
      "index":          list,  # file paths affected in the index
      "head":           dict,  # {from, to, type}
      "warnings":       list,
      "note":           str,   # approximation disclaimer
    }
    """

    def predict(self, repo, parsed: dict) -> dict:
        if repo is None:
            return self._err(parsed, "No repository loaded.")
        if not parsed.get("known"):
            known = ", ".join(GitCommandParser.SUPPORTED)
            return self._err(
                parsed, f"'{parsed['verb']}' is not simulated.\nSupported: {known}"
            )
        handler = getattr(self, f"_{parsed['verb']}", None)
        if handler is None:
            handler = getattr(self, "_checkout")  # switch → checkout fallback
        try:
            return handler(repo, parsed)
        except Exception as exc:
            return self._err(parsed, f"Prediction error: {exc}")

    # ── Shared helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _base(parsed: dict) -> dict:
        return {
            "command": parsed["original"], "verb": parsed["verb"],
            "supported": True, "interpretation": "",
            "objects": [], "refs": [], "index": [],
            "head": {}, "warnings": [], "note": "",
        }

    @staticmethod
    def _obj(type_, action, name, sha_before="", sha_after="", detail="") -> dict:
        return {"type": type_, "action": action, "name": name,
                "sha_before": sha_before, "sha_after": sha_after, "detail": detail}

    @staticmethod
    def _err(parsed: dict, msg: str) -> dict:
        return {"command": parsed.get("original",""), "verb": parsed.get("verb",""),
                "supported": False, "interpretation": msg,
                "objects":[], "refs":[], "index":[], "head":{}, "warnings":[], "note":""}

    @staticmethod
    def _author(repo) -> str:
        try:
            c = repo.config_reader()
            return f"{c.get_value('user','name','Unknown')} <{c.get_value('user','email','?')}>"
        except Exception:
            return "Unknown User <unknown@example.com>"

    @staticmethod
    def _approx_sha(type_: str, tree: str, parent: str,
                    author: str, message: str, extra_parent: str = "") -> str:
        """Compute an approximate git object SHA using git's own header format."""
        ts   = int(time.time())
        body = f"tree {tree}\n"
        if parent:      body += f"parent {parent}\n"
        if extra_parent: body += f"parent {extra_parent}\n"
        body += f"author {author} {ts} +0000\ncommitter {author} {ts} +0000\n\n{message}"
        header = f"{type_} {len(body.encode())}\x00"
        return hashlib.sha1((header + body).encode("utf-8", errors="replace")).hexdigest()

    @staticmethod
    def _head_info(repo) -> tuple:
        """Returns (head_sha, tree_sha, branch_name, is_detached)."""
        try:
            return (repo.head.commit.hexsha, repo.head.commit.tree.hexsha,
                    "(detached)" if repo.head.is_detached else repo.active_branch.name,
                    repo.head.is_detached)
        except Exception:
            return "", "", "(no commits yet)", False

    # ── Verb handlers ─────────────────────────────────────────────────────────

    def _commit(self, repo, parsed: dict) -> dict:
        r       = self._base(parsed)
        flags   = parsed["flags"]
        message = flags.get("-m") or flags.get("--message") or ""
        amend   = "--amend" in flags

        head_sha, tree_sha, branch, detached = self._head_info(repo)

        try:   staged = list(repo.index.diff("HEAD"))
        except: staged = []

        parent_sha = (repo.head.commit.parents[0].hexsha
                      if amend and repo.head.commit.parents else
                      (head_sha if not amend else ""))

        if not staged and not amend and "--allow-empty" not in flags:
            r["warnings"].append(
                "Nothing currently staged — git would abort with 'nothing to commit'."
            )

        msg_display = message or "(editor would open)"
        new_sha = self._approx_sha(
            "commit", tree_sha, parent_sha, self._author(repo),
            message or "placeholder",
        )

        action_str = "Amend last commit" if amend else f"Create new commit on '{branch}'"
        r["interpretation"] = (
            f"{action_str}"
            + (f" with message \"{message}\"" if message else " (no -m flag → editor opens)")
            + f"\n{len(staged)} file(s) currently staged."
        )

        r["objects"] = [
            self._obj("commit", "create", "New commit object",
                      sha_after=new_sha,
                      detail=f"parent: {parent_sha[:12] or 'none'}  msg: \"{msg_display}\""),
            self._obj("tree", "reuse" if not staged else "update", "Root tree",
                      sha_before=tree_sha, sha_after=tree_sha,
                      detail="unchanged" if not staged else f"{len(staged)} file(s) alter tree"),
        ]

        if not detached:
            r["refs"] = [self._obj(
                "branch_ref", "update", f"refs/heads/{branch}",
                sha_before=head_sha, sha_after=new_sha,
                detail=f"{head_sha[:12]} → {new_sha[:12]}",
            )]

        r["head"] = {"from": head_sha, "to": new_sha, "type": "branch"}
        r["index"] = [d.a_path for d in staged]
        r["note"]  = "⚠  SHA is approximate — actual value depends on precise commit timestamp."
        return r

    def _add(self, repo, parsed: dict) -> dict:
        r    = self._base(parsed)
        f    = parsed["flags"]
        args = parsed["args"]

        all_    = "-A" in f or "--all" in f
        update  = "-u" in f or "--update" in f

        try:
            if all_:    paths = [d.a_path for d in repo.index.diff(None)] + list(repo.untracked_files)
            elif update: paths = [d.a_path for d in repo.index.diff(None)]
            else:        paths = args
        except Exception:
            paths = args

        if not paths:
            r["warnings"].append("No paths specified — nothing would be staged.")
            r["interpretation"] = "No files to stage."
            return r

        r["interpretation"] = (
            f"Stage {len(paths)} file path(s) to the index.\n"
            "A new blob object is written to the object store for each modified file "
            "if that exact content does not already exist as a blob."
        )

        for path in paths[:20]:
            full = os.path.join(repo.working_dir, path)
            try:
                data = open(full, "rb").read()
                sha  = hashlib.sha1(
                    f"blob {len(data)}\x00".encode() + data
                ).hexdigest()
            except Exception:
                sha = "(cannot read)"
            r["objects"].append(
                self._obj("blob", "create", os.path.basename(path),
                          sha_after=sha, detail=f"path: {path}")
            )

        if len(paths) > 20:
            r["objects"].append(
                self._obj("…", "…", f"and {len(paths)-20} more files", "", "", ""))

        r["index"] = paths
        r["note"]  = "Blob SHA computed from current file content (git hash-object algorithm)."
        return r

    def _checkout(self, repo, parsed: dict) -> dict:
        r      = self._base(parsed)
        flags  = parsed["flags"]
        args   = parsed["args"]
        create = "-b" in flags or "-B" in flags
        target = args[0] if args else ""

        if not target:
            r["interpretation"] = "No target specified — git would show current branch."
            return r

        head_sha, _, branch, _ = self._head_info(repo)

        try:
            target_sha = repo.rev_parse(target).hexsha
            is_sha     = target_sha not in {b.commit.hexsha for b in repo.branches
                                             if b.commit.hexsha == target_sha}
            # Actually check if target is a branch name
            branch_names = [b.name for b in repo.branches]
            is_detached_after = target not in branch_names
        except Exception:
            target_sha = "(unresolvable)"; is_detached_after = True

        if create:
            r["interpretation"] = (
                f"Create and immediately switch to new branch '{target}' "
                f"pointing to current HEAD ({head_sha[:12]})."
            )
            r["refs"] = [self._obj(
                "branch_ref", "create", f"refs/heads/{target}",
                sha_after=head_sha, detail=f"new branch at {head_sha[:12]}",
            )]
            r["head"] = {"from": head_sha, "to": head_sha, "type": "branch"}
        else:
            warn = " ⚠ → detached HEAD" if is_detached_after else ""
            r["interpretation"] = (
                f"Move HEAD to '{target}' ({target_sha[:12]}){warn}.\n"
                "Files in working directory are updated to match that snapshot."
            )
            if is_detached_after:
                r["warnings"].append(
                    "Checking out a bare SHA enters detached HEAD state. "
                    "Create a branch (-b) before making new commits."
                )
            r["head"] = {
                "from": head_sha, "to": target_sha,
                "type": "detached" if is_detached_after else "branch",
            }

        r["note"] = "Working-directory file changes are not individually listed in this preview."
        return r

    # switch is identical to checkout in this context
    _switch = _checkout

    def _reset(self, repo, parsed: dict) -> dict:
        r      = self._base(parsed)
        flags  = parsed["flags"]
        args   = parsed["args"]
        target = args[0] if args else "HEAD~1"

        soft  = "--soft"  in flags
        hard  = "--hard"  in flags
        mode  = "soft" if soft else ("hard" if hard else "mixed")

        try:
            target_sha = repo.rev_parse(target).hexsha
        except Exception:
            r["warnings"].append(f"Cannot resolve '{target}'.")
            r["interpretation"] = f"Cannot resolve target ref '{target}'."
            return r

        head_sha, _, branch, detached = self._head_info(repo)

        try:   n = sum(1 for _ in repo.iter_commits(f"{target_sha}..{head_sha}"))
        except: n = 0

        effects = {
            "soft":  "Changes from removed commits → index (staged, ready to re-commit).",
            "mixed": "Changes from removed commits → working directory (unstaged, files kept).",
            "hard":  "⚠  Changes from removed commits are PERMANENTLY DISCARDED.",
        }

        r["interpretation"] = (
            f"Move branch '{branch}' back to {target_sha[:12]}, "
            f"removing {n} commit(s) from the branch tip.\n"
            f"Mode: --{mode} — {effects[mode]}"
        )
        r["refs"] = [self._obj(
            "branch_ref", "update", f"refs/heads/{branch}",
            sha_before=head_sha, sha_after=target_sha,
            detail=f"{n} commit(s) removed from tip · {head_sha[:12]} → {target_sha[:12]}",
        )]
        r["head"] = {"from": head_sha, "to": target_sha, "type": "branch"}

        if hard:
            r["warnings"].append(
                "Hard reset permanently overwrites working directory and index. "
                "Recovery is only possible via  git reflog  before garbage collection."
            )
        if n > 0:
            r["warnings"].append(
                f"{n} commit object(s) become unreachable from this branch "
                "(still in object store until  git gc  runs)."
            )
        r["note"] = "git reset never deletes objects — they persist in the object store and reflog."
        return r

    def _branch(self, repo, parsed: dict) -> dict:
        r     = self._base(parsed)
        flags = parsed["flags"]
        args  = parsed["args"]

        delete = "-d" in flags or "-D" in flags or "--delete" in flags
        force  = "-D" in flags

        if not args:
            try:   names = [b.name for b in repo.branches]
            except: names = []
            r["interpretation"] = f"List local branches: {', '.join(names) or '(none)'}"
            r["note"] = "Informational only — no changes made."
            return r

        name = args[0]

        if delete:
            try:   sha = repo.branches[name].commit.hexsha
            except: sha = "(unknown)"
            r["interpretation"] = f"Delete branch '{name}'."
            r["refs"] = [self._obj(
                "branch_ref", "delete", f"refs/heads/{name}",
                sha_before=sha, detail="ref file removed from .git/refs/heads/",
            )]
            if force:
                r["warnings"].append(
                    f"-D bypasses the unmerged check — commits unique to '{name}' "
                    "may become unreachable."
                )
        else:
            start = args[1] if len(args) > 1 else "HEAD"
            try:   start_sha = repo.rev_parse(start).hexsha
            except: start_sha = "(unresolvable)"
            r["interpretation"] = f"Create branch '{name}' pointing to {start_sha[:12]}."
            r["refs"] = [self._obj(
                "branch_ref", "create", f"refs/heads/{name}",
                sha_after=start_sha, detail=f"new ref at {start_sha[:12]}",
            )]

        r["note"] = "Branch operations only modify ref files — no git objects are created or deleted."
        return r

    def _tag(self, repo, parsed: dict) -> dict:
        r        = self._base(parsed)
        flags    = parsed["flags"]
        args     = parsed["args"]
        annotate = "-a" in flags or "--annotate" in flags
        message  = flags.get("-m") or flags.get("--message") or ""

        if not args:
            r["interpretation"] = "List all tags — no changes."
            r["note"] = "Informational only."
            return r

        name, target = args[0], args[1] if len(args) > 1 else "HEAD"

        try:   target_sha = repo.rev_parse(target).hexsha
        except: target_sha = "(unresolvable)"

        if annotate:
            r["interpretation"] = (
                f"Create annotated tag '{name}' at {target_sha[:12]}.\n"
                "An annotated tag creates a tag object in the object store (tagger, date, "
                "message) — it is more than a plain ref, and is recommended for releases."
            )
            r["objects"] = [self._obj(
                "tag", "create", f"Tag object: {name}",
                sha_after="(new tag object SHA)",
                detail=f"tagger: {self._author(repo)}  message: \"{message}\"",
            )]
        else:
            r["interpretation"] = (
                f"Create lightweight tag '{name}' pointing to {target_sha[:12]}.\n"
                "A lightweight tag is just a ref — no tag object is created in the object store."
            )

        r["refs"] = [self._obj(
            "tag_ref", "create", f"refs/tags/{name}",
            sha_after=target_sha, detail=f"points to {target_sha[:12]}",
        )]
        r["note"] = ("Annotated tags create a tag object (-a); "
                     "lightweight tags only create a ref file.")
        return r

    def _revert(self, repo, parsed: dict) -> dict:
        r    = self._base(parsed)
        args = parsed["args"]

        if not args:
            r["interpretation"] = "No SHA specified — git would show usage."
            return r

        target = args[0]
        try:
            tc        = repo.commit(target)
            target_sha = tc.hexsha
            short_msg  = tc.message.split("\n")[0][:50]
            n_files    = len(tc.stats.files)
        except Exception:
            target_sha = "(unresolvable)"; short_msg = ""; n_files = 0

        head_sha, tree_sha, branch, _ = self._head_info(repo)

        revert_msg = f'Revert "{short_msg}"'
        new_sha    = self._approx_sha(
            "commit", tree_sha, head_sha, self._author(repo), revert_msg
        )

        r["interpretation"] = (
            f"Create a new commit on '{branch}' that exactly inverts:\n"
            f"  {target_sha[:12]}  \"{short_msg}\"\n"
            f"This reverses {n_files} file change(s). Nothing is rewritten — "
            "the original commit remains in history."
        )
        r["objects"] = [self._obj(
            "commit", "create", "New revert commit",
            sha_after=new_sha,
            detail=f"msg: '{revert_msg}'  parent: {head_sha[:12]}",
        )]
        r["refs"] = [self._obj(
            "branch_ref", "update", f"refs/heads/{branch}",
            sha_before=head_sha, sha_after=new_sha,
            detail=f"{head_sha[:12]} → {new_sha[:12]}",
        )]
        r["head"] = {"from": head_sha, "to": new_sha, "type": "branch"}
        r["note"] = "⚠  SHA is approximate — actual value depends on precise commit timestamp."
        return r

    def _merge(self, repo, parsed: dict) -> dict:
        r      = self._base(parsed)
        flags  = parsed["flags"]
        args   = parsed["args"]
        no_ff  = "--no-ff"  in flags
        ff_only= "--ff-only" in flags

        if not args:
            r["interpretation"] = "No branch specified."
            return r

        target = args[0]
        try:   target_sha = repo.rev_parse(target).hexsha
        except:
            r["warnings"].append(f"Cannot resolve '{target}'.")
            r["interpretation"] = f"Cannot resolve '{target}'."
            return r

        head_sha, tree_sha, branch, _ = self._head_info(repo)

        try:
            bases = repo.merge_base(head_sha, target_sha)
            is_ff = bool(bases) and bases[0].hexsha == head_sha
        except Exception:
            is_ff = False

        if is_ff and not no_ff:
            r["interpretation"] = (
                f"Fast-forward '{branch}' to '{target}' — no merge commit needed.\n"
                f"'{branch}' is a direct ancestor of '{target}'; "
                "the ref simply advances."
            )
            r["refs"] = [self._obj(
                "branch_ref", "update", f"refs/heads/{branch}",
                sha_before=head_sha, sha_after=target_sha,
                detail="fast-forward — no new object created",
            )]
            r["head"] = {"from": head_sha, "to": target_sha, "type": "branch"}
            r["note"] = "Fast-forward: no merge commit object is written."
        elif ff_only and not is_ff:
            r["warnings"].append(
                "Branches have diverged — fast-forward not possible. "
                "git would abort with --ff-only."
            )
            r["interpretation"] = "Merge would be aborted (--ff-only, non-FF history)."
        else:
            ts   = int(time.time())
            msg  = f"Merge branch '{target}'"
            body = (f"tree {tree_sha}\nparent {head_sha}\nparent {target_sha}\n"
                    f"author {self._author(repo)} {ts} +0000\n"
                    f"committer {self._author(repo)} {ts} +0000\n\n{msg}")
            merge_sha = hashlib.sha1(
                f"commit {len(body.encode())}\x00{body}".encode()
            ).hexdigest()

            r["interpretation"] = (
                f"Three-way merge of '{target}' into '{branch}'.\n"
                "A merge commit with two parents will be created."
            )
            r["objects"] = [self._obj(
                "commit", "create", "Merge commit (2 parents)",
                sha_after=merge_sha,
                detail=f"parents: {head_sha[:12]},  {target_sha[:12]}",
            )]
            r["refs"] = [self._obj(
                "branch_ref", "update", f"refs/heads/{branch}",
                sha_before=head_sha, sha_after=merge_sha,
                detail=f"{head_sha[:12]} → {merge_sha[:12]}",
            )]
            r["head"] = {"from": head_sha, "to": merge_sha, "type": "branch"}
            r["warnings"].append(
                "Conflicts cannot be predicted without running the merge — "
                "inspect manually if branches modify the same lines."
            )
            r["note"] = "⚠  Merge commit SHA is approximate."
        return r

    def _stash(self, repo, parsed: dict) -> dict:
        r   = self._base(parsed)
        sub = parsed["args"][0] if parsed["args"] else "push"

        try:
            n_dirty   = len(list(repo.index.diff(None)))
            n_new     = len(repo.untracked_files)
            head_sha, _, branch, _ = self._head_info(repo)
        except Exception:
            n_dirty = n_new = 0; head_sha = ""; branch = "(unknown)"

        if sub in ("push", "save", ""):
            if n_dirty == 0 and n_new == 0:
                r["warnings"].append("Working tree is clean — nothing to stash.")
            r["interpretation"] = (
                f"Stash {n_dirty} modified + {n_new} untracked file(s).\n"
                "Git creates two commit objects under refs/stash:\n"
                "  • one representing the index state\n"
                "  • one representing the working-directory state\n"
                "Then resets WD and index to HEAD, leaving the tree clean."
            )
            r["objects"] = [
                self._obj("commit","create","Stash index commit",   sha_after="(new SHA)"),
                self._obj("commit","create","Stash WD commit",      sha_after="(new SHA)",
                          detail="parent: stash index commit"),
            ]
            r["refs"] = [self._obj(
                "stash_ref","update","refs/stash",
                sha_before="(previous top)", sha_after="(new stash entry)",
                detail=f"WIP on {branch}: {head_sha[:12]}",
            )]
            r["note"] = "Stash entries are stored as a linked list under refs/stash."
        elif sub == "pop":
            r["interpretation"] = (
                "Apply the top stash entry to WD/index, then remove it from the list."
            )
            r["note"] = "Cannot fully predict outcome — depends on stash vs current WD state."
        elif sub == "list":
            r["interpretation"] = "Show all stash entries — no changes."
        elif sub == "drop":
            r["interpretation"] = "Remove the top stash entry from refs/stash."
            r["refs"] = [self._obj(
                "stash_ref","update","refs/stash",
                sha_before="(current top)", sha_after="(next entry)",
                detail="stash entry removed",
            )]
        return r

class CommandPreviewWidget(QWidget):
    """
    Phase 4.6 — Command ↔ Internal Changes Panel.

    Layout
    ------
    ┌─ input bar (always 36 px) ──────────────────────────────────────┐
    │  git  [__command input________________________]  [Preview ▶] [▾] │
    └─────────────────────────────────────────────────────────────────┘
    ┌─ QTreeWidget results (hidden until first use) ──────────────────┐
    │  ▼ Command Interpretation                                        │
    │  ▼ Git Object Changes                                            │
    │  ▼ Ref / Branch Updates                                          │
    │  ▼ HEAD Movement                                                 │
    │  ▼ Index / Staging Changes                                       │
    │  ▼ Warnings                                                      │
    │    ℹ  This preview is read-only — no git operations executed     │
    └─────────────────────────────────────────────────────────────────┘

    The user may omit the leading 'git' — it is prepended automatically.
    The engine predicts effects based on current repo state without
    executing anything. SHA values for new objects are approximate
    (computed with the current timestamp as the author/committer time).
    """

    def __init__(self, state: AppState):
        super().__init__()
        self._state     = state
        self._predictor = GitCommandPredictor()
        self._shown     = False

        self.setObjectName("cmdPanel")
        self.setMinimumHeight(36)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Input bar (always visible) ────────────────────────────────────────
        bar = QWidget()
        bar.setObjectName("cmdBar")
        bar.setFixedHeight(36)
        bl  = QHBoxLayout(bar)
        bl.setContentsMargins(10, 0, 8, 0)
        bl.setSpacing(8)

        prefix = QLabel("git")
        prefix.setStyleSheet(
            f"color:{ACCENT_GREEN}; font-size:12px; font-weight:700;"
            f" font-family:'SF Mono','Menlo','Consolas',monospace; background:transparent;"
        )
        bl.addWidget(prefix)

        self._input = QLineEdit()
        self._input.setObjectName("cmdInput")
        self._input.setPlaceholderText(
            "commit -m \"msg\"  ·  add src/  ·  reset --soft HEAD~1  "
            "·  checkout main  ·  merge feature  …"
        )
        self._input.returnPressed.connect(self._run)
        bl.addWidget(self._input)

        self._run_btn = QPushButton("Preview ▶")
        self._run_btn.setObjectName("cmdPreviewBtn")
        self._run_btn.setFixedHeight(26)
        self._run_btn.clicked.connect(self._run)
        bl.addWidget(self._run_btn)

        self._toggle_btn = QPushButton("▾")
        self._toggle_btn.setObjectName("cmdToggleBtn")
        self._toggle_btn.setFixedSize(26, 26)
        self._toggle_btn.clicked.connect(self._toggle)
        bl.addWidget(self._toggle_btn)

        root.addWidget(bar)

        # ── Results tree (hidden by default) ──────────────────────────────────
        self._tree = QTreeWidget()
        self._tree.setObjectName("cmdTree")
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setIndentation(18)
        self._tree.setAnimated(True)
        self._tree.hide()
        root.addWidget(self._tree)

        state.repo_changed.connect(lambda _: self._tree.clear())

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _run(self):
        raw = self._input.text().strip()
        if not raw:
            return
        if not raw.lower().startswith("git ") and not raw.lower() == "git":
            raw = "git " + raw

        parsed = GitCommandParser.parse(raw)
        if parsed is None:
            self._show_error("Cannot parse command — check for unclosed quotes.")
            return

        result = self._predictor.predict(self._state.repo, parsed)
        self._render(result)

        if not self._shown:
            self._toggle()

        self._state.logger.log(
            f"Command preview: {raw[:60]}  →  "
            f"{'supported' if result['supported'] else 'unsupported'}"
        )

    def _toggle(self):
        self._shown = not self._shown
        self._tree.setVisible(self._shown)
        self._toggle_btn.setText("▴" if self._shown else "▾")

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render(self, r: dict):
        self._tree.clear()

        # ① Command + interpretation
        interp_rows = [("Interpretation", r["interpretation"], TEXT_PRIMARY)]
        if not r["supported"]:
            self._section("📋  Command", r["command"], interp_rows, expand=True)
            return

        interp_rows += [
            ("Verb",      r["verb"],                                    TEXT_SECONDARY),
            ("Supported", "Yes",                                        ACCENT_GREEN),
        ]
        self._section("📋  Command", r["command"], interp_rows, expand=True)

        # ② Git objects
        obj_rows = []
        for o in r.get("objects", []):
            sha = (f"{o['sha_before'][:10]} → {o['sha_after'][:10]}"
                   if o["sha_before"] and o["sha_after"] else
                   f"new: {o['sha_after'][:12]}" if o["sha_after"] else "")
            color = {"create": ACCENT_GREEN, "update": ACCENT_ORANGE,
                     "delete": ACCENT_RED, "reuse": TEXT_TERTIARY}.get(o["action"], TEXT_SECONDARY)
            label = f"{o['type'].upper():<8}  [{o['action']}]  {o['name']}"
            obj_rows.append((label, f"{sha}  {o['detail']}", color))

        self._section(
            f"⬡  Git Object Changes  ({len(obj_rows)})", None,
            obj_rows or [("No new objects created", "", TEXT_TERTIARY)],
            expand=bool(obj_rows),
        )

        # ③ Ref updates
        ref_rows = []
        for ref in r.get("refs", []):
            color = {"create": ACCENT_GREEN, "update": ACCENT_ORANGE,
                     "delete": ACCENT_RED}.get(ref["action"], TEXT_SECONDARY)
            label = f"{ref['type'].replace('_ref','').upper():<10}  [{ref['action']}]  {ref['name']}"
            ref_rows.append((label, ref["detail"], color))

        self._section(
            f"⎇  Ref / Branch Updates  ({len(ref_rows)})", None,
            ref_rows or [("No ref changes", "", TEXT_TERTIARY)],
            expand=bool(ref_rows),
        )

        # ④ HEAD movement
        head = r.get("head", {})
        if head and head.get("from") or head.get("to"):
            frm, to, typ = head.get("from",""), head.get("to",""), head.get("type","")
            if frm == to:
                head_rows = [("HEAD stays", f"{frm[:12]}  ({typ})", TEXT_SECONDARY)]
            else:
                head_rows = [("HEAD moves",
                              f"{frm[:12] or '∅'} → {to[:12] or '∅'}  [{typ}]",
                              ACCENT_ORANGE)]
        else:
            head_rows = [("HEAD does not move", "", TEXT_TERTIARY)]

        self._section("◆  HEAD Movement", None, head_rows, expand=True)

        # ⑤ Index changes
        idx = r.get("index", [])
        idx_rows = [(f"  {p}", "would be staged", TEXT_SECONDARY) for p in idx[:15]]
        if len(idx) > 15:
            idx_rows.append((f"  … and {len(idx)-15} more", "", TEXT_TERTIARY))
        self._section(
            f"□  Index / Staging Changes  ({len(idx)})", None,
            idx_rows or [("No index changes", "", TEXT_TERTIARY)],
            expand=False,
        )

        # ⑥ Warnings + notes
        warn_rows = [(f"⚠  {w}", "", ACCENT_ORANGE) for w in r.get("warnings", [])]
        if r.get("note"):
            warn_rows.append((r["note"], "", TEXT_TERTIARY))
        if warn_rows:
            self._section(f"⚠  Warnings  ({len(warn_rows)})", None, warn_rows, expand=True)

        # Footer disclaimer
        foot = QTreeWidgetItem(self._tree)
        foot.setText(0, "  ℹ  Read-only simulation — no git operations were executed.")
        foot.setForeground(0, QColor(TEXT_TERTIARY))
        f = foot.font(0); f.setItalic(True); foot.setFont(0, f)

    def _section(self, title: str, subtitle: "str | None",
                 rows: list, expand: bool = True):
        """Add a collapsible top-level section."""
        sect = QTreeWidgetItem(self._tree)
        sect.setText(0, title)
        f = sect.font(0); f.setBold(True); f.setPointSize(11); sect.setFont(0, f)
        sect.setForeground(0, QColor(TEXT_PRIMARY))

        if subtitle:
            s = QTreeWidgetItem(sect)
            s.setText(0, f"   {subtitle}")
            s.setForeground(0, QColor(TEXT_SECONDARY))

        for label, detail, color in rows:
            row = QTreeWidgetItem(sect)
            combined = f"   {label}{'    ' + detail if detail else ''}"
            row.setText(0, combined)
            row.setForeground(0, QColor(color))

        sect.setExpanded(expand)

    def _show_error(self, msg: str):
        self._tree.clear()
        item = QTreeWidgetItem(self._tree)
        item.setText(0, f"⚠  {msg}")
        item.setForeground(0, QColor(ACCENT_RED))
        if not self._shown:
            self._toggle()