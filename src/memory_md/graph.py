"""Render the [[link]] graph of a memory repo.

Formats: mermaid (renders natively in GitHub markdown), dot (Graphviz),
json (for other tools), list (plain text edges).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .repo import MemoryRepo


def _node_id(relpath: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", relpath.as_posix())


def _edges(repo: MemoryRepo) -> list[tuple[Path, Path]]:
    out = []
    for note in repo.files.values():
        for link in note.links:
            target = repo.resolve(link.path)
            if target is not None:
                out.append((note.relpath, target.relpath))
    return out


def to_mermaid(repo: MemoryRepo, direction: str = "LR") -> str:
    lines = [f"graph {direction}"]
    nodes = sorted(repo.files.keys(), key=lambda p: p.as_posix())
    for rel in nodes:
        nid = _node_id(rel)
        label = rel.as_posix()
        if rel == Path("MEMORY.md"):
            lines.append(f'    {nid}["**{label}**"]')
        else:
            lines.append(f'    {nid}["{label}"]')
    for src, dst in _edges(repo):
        lines.append(f"    {_node_id(src)} --> {_node_id(dst)}")
    return "\n".join(lines)


def to_dot(repo: MemoryRepo) -> str:
    edges = _edges(repo)
    connected = {p for e in edges for p in e}
    lines = ["digraph memory {", "    rankdir=LR;", "    node [shape=box];"]
    for src, dst in edges:
        lines.append(f'    "{src.as_posix()}" -> "{dst.as_posix()}";')
    for rel in repo.files:
        if rel not in connected:
            lines.append(f'    "{rel.as_posix()}" [style=dashed];')
    lines.append("}")
    return "\n".join(lines)


def to_json(repo: MemoryRepo) -> str:
    edges = _edges(repo)
    return json.dumps(
        {
            "root": str(repo.root),
            "nodes": [p.as_posix() for p in sorted(repo.files, key=lambda x: x.as_posix())],
            "edges": [
                {"from": s.as_posix(), "to": d.as_posix()} for s, d in edges
            ],
        },
        indent=2,
    )


def to_list(repo: MemoryRepo) -> str:
    lines = []
    edges = _edges(repo)
    for note in sorted(repo.files.values(), key=lambda n: n.relpath.as_posix()):
        targets = [d.as_posix() for s, d in edges if s == note.relpath]
        if targets:
            lines.append(f"{note.relpath.as_posix()} -> {', '.join(targets)}")
        else:
            lines.append(f"{note.relpath.as_posix()} (no outgoing links)")
    return "\n".join(lines)


RENDERERS = {"mermaid": to_mermaid, "dot": to_dot, "json": to_json, "list": to_list}
