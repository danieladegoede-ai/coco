"""Approved syntax-tree data types and builder protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class NodeKind(str, Enum):
    ROOT = "root"
    INNER = "inner"
    LEAF = "leaf"


@dataclass(slots=True)
class TreeNode:
    node_id: int
    kind: NodeKind
    contents: str
    parent_id: int | None
    child_ids: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.node_id < 1:
            raise ValueError("Tree node IDs must be one or greater.")
        if not self.contents:
            raise ValueError("Tree node contents cannot be empty.")
        if self.kind is NodeKind.ROOT and self.parent_id is not None:
            raise ValueError("The root node cannot have a parent.")
        if self.kind is not NodeKind.ROOT and self.parent_id is None:
            raise ValueError("Every non-root node requires a parent ID.")
        if self.kind is NodeKind.LEAF and self.child_ids:
            raise ValueError("Leaf nodes cannot have children.")


class TreeBuilder(Protocol):
    """Parser-facing interface implemented by the concrete syntax tree."""

    def add_root(self, contents: str) -> TreeNode: ...

    def add_inner(self, contents: str, parent_id: int) -> TreeNode: ...

    def add_leaf(self, contents: str, parent_id: int) -> TreeNode: ...

    def validate(self) -> None: ...
