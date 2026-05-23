import heapq
from dataclasses import dataclass, field
from typing import Optional

import git


@dataclass
class CommitNode:
    """
    Immutable identity fields are set at construction time.
    Graph-topology fields (child_shas, labels) are populated by DAGLayout.
    Position fields (x, y, parent_cols) are written by the lane-assignment pass.

    x           — column (lane index, 0 = leftmost / primary branch)
    y           — row    (0 = newest commit, increases toward the root)
    parent_cols — column index of each parent, in parent_shas order.
                  parent_cols[0] is the primary-parent column (usually == x).
                  parent_cols[1:] are the incoming merge columns.
                  The renderer uses this to draw connecting segments and
                  diagonal merge curves without re-deriving lane positions.
    """

    sha:         str
    short_sha:   str
    message:     str
    author:      str
    date:        int

    parent_shas: list[str] = field(default_factory=list)
    child_shas:  list[str] = field(default_factory=list)
    labels:      list[str] = field(default_factory=list)

    x:           int       = 0
    y:           int       = 0
    parent_cols: list[int] = field(default_factory=list) 
    # lane positions 

# ─────────────────────────────────────────────────────────────────────────────
# DAGLayout — walks the repo, sorts commits, assigns grid positions
# ─────────────────────────────────────────────────────────────────────────────

class DAGLayout:
    """
    Converts a git.Repo into a positioned grid of CommitNodes.

    Usage::

        layout  = DAGLayout()
        nodes, col_count = layout.build(repo)

    ``nodes``     — list[CommitNode] ordered newest-first (nodes[0] is HEAD).
    ``col_count`` — number of columns occupied (width of the grid).

    The grid is sized dynamically: row count equals len(nodes) and column
    count equals the peak number of simultaneously live branch lanes.
    """

    MAX_COMMITS: int = 2000

    def build(self, repo: git.Repo) -> tuple[list[CommitNode], int]:
        nodes   = self._collect(repo)
        ordered = self._topo_sort(nodes)
        self._assign_labels(repo, nodes)
        self._assign_positions(ordered)
        col_count = max((n.x for n in ordered), default=0) + 1
        return ordered, col_count

    # ── Collection ────────────────────────────────────────────────────────────

    def _collect(self, repo: git.Repo) -> dict[str, CommitNode]:
        """
        Walk every reachable commit up to MAX_COMMITS using git's own
        topo-order (children before parents, date-sorted within a level).
        A second pass wires up child_shas from the parent_shas lists.
        """
        nodes: dict[str, CommitNode] = {}

        for commit in repo.iter_commits(
            "--all", max_count=self.MAX_COMMITS, topo_order=True
        ):
            sha = commit.hexsha
            if sha in nodes:
                continue
            nodes[sha] = CommitNode(
                sha = sha,
                short_sha = sha[:7],
                message = commit.message.split("\n", 1)[0].strip(),
                author = commit.author.name or commit.author.email,
                date = commit.committed_date,
                parent_shas = [p.hexsha for p in commit.parents],
            )

        for node in nodes.values():
            for p_sha in node.parent_shas:
                if p_sha in nodes:
                    nodes[p_sha].child_shas.append(node.sha)

        return nodes

    # ── Label assignment ──────────────────────────────────────────────────────

    def _assign_labels(self, repo: git.Repo, nodes: dict[str, CommitNode]):
        """
        Attach human-readable ref names to CommitNodes.

        Local branches  — plain name; the checked-out branch gets a "● " prefix.
        Remote refs     — full refname (origin/main, etc.).
        Tags            — "tag: <name>".
        Detached HEAD   — "HEAD" inserted at position 0.
        """
        try:
            active = repo.active_branch.name
        except TypeError:
            active = None

        for branch in repo.branches:
            sha = branch.commit.hexsha
            if sha not in nodes:
                continue
            lbl = f"\u25cf {branch.name}" if branch.name == active else branch.name
            nodes[sha].labels.append(lbl)

        for remote in repo.remotes:
            for ref in remote.refs:
                try:
                    sha = ref.commit.hexsha
                except Exception:
                    continue
                if sha in nodes:
                    nodes[sha].labels.append(ref.name)

        for tag in repo.tags:
            try:
                sha = tag.commit.hexsha
            except Exception:
                continue
            if sha in nodes:
                nodes[sha].labels.append(f"tag: {tag.name}")

        if active is None:
            sha = repo.head.commit.hexsha
            if sha in nodes:
                nodes[sha].labels.insert(0, "HEAD")

    # ── Topological sort ──────────────────────────────────────────────────────

    def _topo_sort(self, nodes: dict[str, CommitNode]) -> list[CommitNode]:
        """
        Kahn's algorithm adapted for a commit DAG.

        Edges point child → parent (commit.parents).  We want to emit
        children before parents, so in_degree[sha] counts how many of
        sha's *children* have not yet been emitted.  The ready-set starts
        with branch-tip commits (in_degree == 0).  A min-heap keyed on
        (-date, sha) breaks ties so that newer commits surface first.
        """
        in_degree: dict[str, int] = {sha: 0 for sha in nodes}
        for node in nodes.values():
            for p_sha in node.parent_shas:
                if p_sha in nodes:
                    in_degree[p_sha] += 1

        heap: list[tuple[int, str]] = []
        for sha, node in nodes.items():
            if in_degree[sha] == 0:
                heapq.heappush(heap, (-node.date, sha))

        ordered: list[CommitNode] = []
        while heap:
            _, sha = heapq.heappop(heap)
            node   = nodes[sha]
            ordered.append(node)
            for p_sha in node.parent_shas:
                if p_sha not in nodes:
                    continue
                in_degree[p_sha] -= 1
                if in_degree[p_sha] == 0:
                    heapq.heappush(heap, (-nodes[p_sha].date, p_sha))

        return ordered

    # ── Lane / column assignment ──────────────────────────────────────────────

    def _assign_positions(self, ordered: list[CommitNode]):
        """
        Single-pass lane-parking algorithm (newest-first).

        Two parallel structures are kept in sync at all times:
          lanes[col]       — SHA expected to arrive in col next, or None (free)
          sha_to_col[sha]  — O(1) reverse map: sha → its current col

        Invariant: lanes[c] == s  ↔  sha_to_col[s] == c

        Pass rules
        ----------
        Claim  — if sha is already in sha_to_col, pop it and take that col;
                  otherwise grab the first free slot (_free_lane).
                  Either way, col is left as None after the commit is drawn.

        Forward (first parent)
          • p0 already in sha_to_col  →  fork case: two children share p0.
            The current col is freed; p0 keeps its existing column.
            parent_cols[0] = sha_to_col[p0].
          • p0 not in sha_to_col  →  normal continuation: p0 inherits col.
            parent_cols[0] = col.

        Forward (extra parents — merge commit)
          • Already in sha_to_col  →  another branch already claimed it;
            record that column, make no new allocation.
          • Not in sha_to_col  →  allocate a new free slot for this parent.

        parent_cols is stored on the node so the renderer can draw
        connecting segments and diagonal merge curves directly.
        """
        lanes:      list[Optional[str]] = []
        sha_to_col: dict[str, int]      = {}

        for row, node in enumerate(ordered):
            sha = node.sha

            if sha in sha_to_col:
                col         = sha_to_col.pop(sha)
                lanes[col]  = None
            else:
                col = self._free_lane(lanes)

            node.x = col
            node.y = row

            parent_cols: list[int] = []
            parents = node.parent_shas

            if parents:
                p0 = parents[0]
                if p0 in sha_to_col:
                    parent_cols.append(sha_to_col[p0])
                else:
                    lanes[col]     = p0
                    sha_to_col[p0] = col
                    parent_cols.append(col)

                for p_sha in parents[1:]:
                    if p_sha in sha_to_col:
                        parent_cols.append(sha_to_col[p_sha])
                    else:
                        slot              = self._free_lane(lanes)
                        lanes[slot]       = p_sha
                        sha_to_col[p_sha] = slot
                        parent_cols.append(slot)

            node.parent_cols = parent_cols
            self._trim_lanes(lanes)

    @staticmethod
    def _free_lane(lanes: list[Optional[str]]) -> int:
        """Return the index of the first None slot, appending one if needed."""
        for i, v in enumerate(lanes):
            if v is None:
                return i
        lanes.append(None)
        return len(lanes) - 1

    @staticmethod
    def _trim_lanes(lanes: list[Optional[str]]):
        """Remove trailing None entries so lane count reflects actual usage."""
        while lanes and lanes[-1] is None:
            lanes.pop()