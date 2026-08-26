import heapq
from dataclasses import dataclass, field
from typing import Optional

import git
from git.objects import Commit as GitCommit


@dataclass
class CommitNode:
    sha:str
    short_sha:str
    message:str
    author:str
    date:int

    parent_shas:list[str] = field(default_factory=list)
    child_shas:list[str] = field(default_factory=list)
    labels:list[str] = field(default_factory=list)

    x:int = 0
    y:int = 0
    parent_cols: list[int] = field(default_factory=list) 


class DAGLayout:
    MAX_COMMITS: int = 2000

    @staticmethod
    def _safe_sha(obj) -> "str | None":
        try:
            sha = obj.hexsha
            if isinstance(sha, (bytes, bytearray)):
                sha = sha.decode("ascii")
            return sha if isinstance(sha, str) and len(sha) == 40 else None
        except Exception:
            return None

    @staticmethod
    def _peel_to_commit(obj) -> "GitCommit | None":
        seen = set()
        while obj is not None:
            oid = id(obj)
            if oid in seen:
                return None
            seen.add(oid)
            if isinstance(obj, GitCommit):
                return obj

            obj = getattr(obj, "object", None)
        return None


    def build(self, repo: git.Repo) -> tuple[list[CommitNode], int]:
        nodes   = self._collect(repo)
        ordered = self._topo_sort(nodes)
        self._assign_labels(repo, nodes)
        self._assign_positions(ordered)
        col_count = max((n.x for n in ordered), default=0) + 1
        return ordered, col_count


    def _collect(self, repo: git.Repo) -> dict[str, CommitNode]:
        nodes: dict[str, CommitNode] = {}

        for commit in repo.iter_commits("--all", max_count=self.MAX_COMMITS, topo_order=True):
            if not isinstance(commit, GitCommit):
                continue

            sha = self._safe_sha(commit)
            if sha is None or sha in nodes:
                continue

            parent_shas: list[str] = []
            for p in commit.parents:
                p_sha = self._safe_sha(p)
                if p_sha:
                    parent_shas.append(p_sha)

            try:
                author = commit.author.name or commit.author.email or "unknown"
                message = commit.message.split("\n", 1)[0].strip()
                date = commit.committed_date
            except Exception:
                continue
            
            nodes[sha] = CommitNode(
                sha         = sha,
                short_sha   = sha[:7],
                message     = message,
                author      = author,
                date        = date,
                parent_shas = parent_shas,
            )

        for node in nodes.values():
            for p_sha in node.parent_shas:
                if p_sha in nodes:
                    nodes[p_sha].child_shas.append(node.sha)

        return nodes


    def _assign_labels(self, repo: git.Repo, nodes: dict[str, CommitNode]):
        try:
            active = repo.active_branch.name
        except TypeError:
            active = None

        for branch in repo.branches:
            try:
                sha = self._safe_sha(branch.commit)
            except Exception:
                continue
            if sha is None or sha not in nodes:
                continue
            lbl = f"\u25cf {branch.name}" if branch.name == active else branch.name
            nodes[sha].labels.append(lbl)

        for remote in repo.remotes:
            for ref in remote.refs:
                try:
                    sha = self._safe_sha(ref.commit)
                except Exception:
                    continue
                if sha and sha in nodes:
                    nodes[sha].labels.append(ref.name)

        for tag in repo.tags:
            try:
                commit = self._peel_to_commit(tag.object)
                if commit is None:
                    continue
                sha = self._safe_sha(commit)
            except Exception:
                continue
            if sha and sha in nodes:
                nodes[sha].labels.append(f"tag: {tag.name}")

        if active is None:
            try:
                sha = self._safe_sha(repo.head.commit)
                if sha and sha in nodes:
                    nodes[sha].labels.insert(0, "HEAD")
            except Exception:
                pass


    def _topo_sort(self, nodes: dict[str, CommitNode]) -> list[CommitNode]:
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


    def _assign_positions(self, ordered: list[CommitNode]):
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