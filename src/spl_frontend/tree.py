"""Approved syntax-tree data types and builder protocol."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class NodeKind(str, Enum):
    ROOT = "root"
    INNER = "inner"
    LEAF = "leaf"


def _is_positive_id(value: object) -> bool:
    """Exclude bool and float keys that compare equal to integer node IDs."""
    return type(value) is int and value > 0


@dataclass(slots=True)
class TreeNode:
    node_id: int
    kind: NodeKind
    contents: str
    parent_id: int | None
    child_ids: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not _is_positive_id(self.node_id):
            raise ValueError("Tree node ID must be a positive integer.")
        if not isinstance(self.kind, NodeKind):
            raise ValueError("Invalid tree node kind.")
        if not isinstance(self.contents, str) or not self.contents.strip():
            raise ValueError("Node contents must be a non-empty string.")
        if self.kind is NodeKind.ROOT:
            if self.contents != "SPL_PROG":
                raise ValueError("Root contents must be SPL_PROG.")
            if self.parent_id is not None:
                raise ValueError("The root node cannot have a parent.")
        elif not _is_positive_id(self.parent_id):
            raise ValueError("Non-root node parent ID must be a positive integer.")
        if not isinstance(self.child_ids, list):
            raise ValueError("Node child IDs must be a list.")
        if any(not _is_positive_id(child_id) for child_id in self.child_ids):
            raise ValueError("Each child ID must be a positive integer.")
        if self.kind is NodeKind.LEAF and self.child_ids:
            raise ValueError("Leaf nodes cannot have children.")
        if self.kind is NodeKind.LEAF and self.contents == "$":
            raise ValueError("The EOF marker '$' cannot be a leaf.")


class TreeBuilder(Protocol):
    """Parser-facing interface implemented by the concrete syntax tree."""

    def add_root(self, contents: str) -> TreeNode: ...

    def add_inner(self, contents: str, parent_id: int) -> TreeNode: ...

    def add_leaf(self, contents: str, parent_id: int) -> TreeNode: ...

    def validate(self) -> None: ...


class SyntaxTree:
    """Build an ordered concrete syntax tree with tree-local, sequential IDs.

    The parser supplies grammar contents and parent IDs; this builder assigns
    every node ID and appends each child to its parent. The root must contain
    ``SPL_PROG`` and the EOF marker ``$`` cannot be a leaf. The approved
    ``TreeNode`` contract is mutable, so read access returns live nodes;
    callers must not edit their fields or private storage. Validation checks
    the entire structure after parsing and before XML publication. XML output
    is the responsibility of a separate module.

    Example parser calls::

        tree = SyntaxTree()
        root = tree.add_root("SPL_PROG")
        program = tree.add_inner("P", root.node_id)
        declarations = tree.add_inner("V_DECL", program.node_id)
        colon = tree.add_leaf(":", program.node_id)
        tree.validate()  # after complete parsing
    """

    def __init__(self) -> None:
        self._nodes: dict[int, TreeNode] = {}
        self._next_id = 1

    @property
    def root(self) -> TreeNode | None:
        """Return the managed root node, or None before one is added.

        Like ``get_node``, this is a live node; treat its fields as read-only.
        """
        return next(
            (node for node in self._nodes.values() if node.kind is NodeKind.ROOT),
            None,
        )

    def __len__(self) -> int:
        """Return the number of nodes in the tree."""
        return len(self._nodes)

    def get_node(self, node_id: int) -> TreeNode:
        """Return the managed node with ``node_id``; do not mutate it."""
        if not _is_positive_id(node_id):
            raise ValueError("Node ID must be a positive integer.")
        try:
            return self._nodes[node_id]
        except KeyError as exc:
            raise ValueError(f"Node ID {node_id!r} does not exist.") from exc

    def iter_nodes(self) -> Iterator[TreeNode]:
        """Yield managed nodes in ascending ID order; do not mutate them."""
        for node_id in sorted(self._nodes):
            yield self._nodes[node_id]

    def add_root(self, contents: str) -> TreeNode:
        """Add the sole SPL_PROG root; reject invalid contents or another root."""
        self._require_contents(contents)
        if self._nodes:
            raise ValueError("A syntax tree can have only one root.")
        if contents != "SPL_PROG":
            raise ValueError("Root contents must be SPL_PROG.")
        node = TreeNode(self._next_id, NodeKind.ROOT, contents, None)
        self._nodes[node.node_id] = node
        self._next_id += 1
        return node

    def add_inner(self, contents: str, parent_id: int) -> TreeNode:
        """Add an inner node beneath an existing root or inner node."""
        return self._add_child(NodeKind.INNER, contents, parent_id)

    def add_leaf(self, contents: str, parent_id: int) -> TreeNode:
        """Add a terminal leaf beneath an existing root or inner node."""
        return self._add_child(NodeKind.LEAF, contents, parent_id)

    @staticmethod
    def _require_contents(contents: str) -> None:
        if not isinstance(contents, str) or not contents.strip():
            raise ValueError("Node contents must be a non-empty string.")

    def _add_child(
        self, kind: NodeKind, contents: str, parent_id: int
    ) -> TreeNode:
        self._require_contents(contents)
        if kind is NodeKind.LEAF and contents == "$":
            raise ValueError("The EOF marker '$' cannot be a leaf.")
        if not _is_positive_id(parent_id):
            raise ValueError("Parent ID must be a positive integer.")
        try:
            parent = self._nodes[parent_id]
        except KeyError as exc:
            raise ValueError(f"Parent ID {parent_id!r} does not exist.") from exc
        if parent.kind is NodeKind.LEAF:
            raise ValueError(f"Leaf node {parent_id} cannot have children.")
        if parent.kind not in (NodeKind.ROOT, NodeKind.INNER):
            raise ValueError(f"Node {parent_id} has an invalid parent kind.")
        node = TreeNode(self._next_id, kind, contents, parent_id)
        parent.child_ids.append(node.node_id)
        self._nodes[node.node_id] = node
        self._next_id += 1
        return node

    def validate(self) -> None:
        """Raise ValueError for any malformed node, link, cycle or orphan.

        The check examines even nodes inserted or changed outside the builder.
        It traverses iteratively, so deep valid trees do not hit the recursion
        limit. The tree is never changed by validation.
        """
        if not self._nodes:
            raise ValueError("Syntax tree has no root.")

        seen_ids: set[int] = set()
        roots: list[TreeNode] = []
        for key, node in self._nodes.items():
            if not isinstance(node, TreeNode):
                raise ValueError(f"Entry {key!r} is not a TreeNode.")
            if not _is_positive_id(key):
                raise ValueError(f"Node mapping key {key!r} is invalid.")
            if not _is_positive_id(node.node_id):
                raise ValueError(f"Node {node.node_id!r} has an invalid ID.")
            if node.node_id in seen_ids:
                raise ValueError(f"Duplicate node ID {node.node_id}.")
            seen_ids.add(node.node_id)
            if key != node.node_id:
                raise ValueError(
                    f"Node mapping key {key!r} differs from node ID {node.node_id}."
                )
            if not isinstance(node.contents, str) or not node.contents.strip():
                raise ValueError(f"Node {node.node_id} has invalid contents.")
            if not isinstance(node.kind, NodeKind):
                raise ValueError(f"Node {node.node_id} has invalid kind {node.kind!r}.")
            if not isinstance(node.child_ids, list):
                raise ValueError(f"Node {node.node_id} has invalid child IDs.")
            if node.kind is NodeKind.ROOT:
                roots.append(node)
                if node.contents != "SPL_PROG":
                    raise ValueError(
                        f"Root node {node.node_id} contents must be SPL_PROG."
                    )
            elif node.kind is NodeKind.LEAF and node.contents == "$":
                raise ValueError(
                    f"Node {node.node_id} has forbidden EOF marker '$' as a leaf."
                )

        if not roots:
            raise ValueError("Syntax tree has no root.")
        if len(roots) > 1:
            raise ValueError(f"Syntax tree has {len(roots)} root nodes.")
        root = roots[0]
        if root.parent_id is not None:
            raise ValueError(f"Root node {root.node_id} cannot have a parent.")

        for node in self.iter_nodes():
            if node.kind is NodeKind.ROOT:
                continue
            if node.parent_id is None:
                raise ValueError(f"Non-root node {node.node_id} has no parent.")
            if type(node.parent_id) is not int or node.parent_id < 1:
                raise ValueError(
                    f"Node {node.node_id} has invalid parent ID {node.parent_id!r}."
                )

        listed_under: dict[int, int] = {}
        for parent in self.iter_nodes():
            if parent.kind is NodeKind.LEAF and parent.child_ids:
                raise ValueError(f"Leaf node {parent.node_id} has children.")
            local_children: set[int] = set()
            for child_id in parent.child_ids:
                if type(child_id) is not int or child_id < 1:
                    raise ValueError(
                        f"Parent {parent.node_id} has invalid child ID {child_id!r}."
                    )
                if child_id in local_children:
                    raise ValueError(
                        f"Parent {parent.node_id} lists child {child_id} twice."
                    )
                local_children.add(child_id)
                if child_id not in self._nodes:
                    raise ValueError(
                        f"Parent {parent.node_id} lists missing child {child_id}."
                    )
                if child_id in listed_under:
                    raise ValueError(
                        f"Child {child_id} is listed under both parents "
                        f"{listed_under[child_id]} and {parent.node_id}."
                    )
                listed_under[child_id] = parent.node_id

        # Inspect every component, including cycles disconnected from the root.
        state: dict[int, int] = {}
        for start in sorted(self._nodes):
            if state.get(start):
                continue
            state[start] = 1
            stack: list[tuple[int, Iterator[int]]] = [
                (start, iter(self._nodes[start].child_ids))
            ]
            while stack:
                parent_id, children = stack[-1]
                child_id = next(children, None)
                if child_id is None:
                    state[parent_id] = 2
                    stack.pop()
                elif state.get(child_id) == 1:
                    raise ValueError(
                        f"Cycle detected through parent {parent_id} and child {child_id}."
                    )
                elif not state.get(child_id):
                    state[child_id] = 1
                    stack.append((child_id, iter(self._nodes[child_id].child_ids)))

        reached: set[int] = set()
        pending = [root.node_id]
        while pending:
            node_id = pending.pop()
            if node_id in reached:
                continue
            reached.add(node_id)
            pending.extend(reversed(self._nodes[node_id].child_ids))
        unreachable = self._nodes.keys() - reached

        for child in self.iter_nodes():
            if child.kind is NodeKind.ROOT:
                continue
            parent = self._nodes.get(child.parent_id)
            if parent is None:
                orphan_note = (
                    f" Node {child.node_id} is unreachable from root {root.node_id}."
                    if child.node_id in unreachable else ""
                )
                raise ValueError(
                    f"Node {child.node_id} refers to missing parent "
                    f"{child.parent_id}.{orphan_note}"
                )
            if parent.kind is NodeKind.LEAF:
                raise ValueError(
                    f"Node {child.node_id} has leaf parent {parent.node_id}."
                )
            listed_parent = listed_under.get(child.node_id)
            if listed_parent is None:
                orphan_note = (
                    f" Node {child.node_id} is unreachable from root {root.node_id}."
                    if child.node_id in unreachable else ""
                )
                raise ValueError(
                    f"Node {child.node_id} is missing from parent "
                    f"{parent.node_id}'s child IDs.{orphan_note}"
                )
            if listed_parent != parent.node_id:
                raise ValueError(
                    f"Child {child.node_id} is listed under parent {listed_parent} "
                    f"but points to parent {parent.node_id}."
                )

        if unreachable:
            missing = min(unreachable)
            raise ValueError(
                f"Node {missing} is unreachable from root {root.node_id}."
            )

        if root.node_id != 1:
            raise ValueError(f"Root node ID must be 1, found {root.node_id}.")
        for expected_id, node_id in enumerate(sorted(seen_ids), start=1):
            if node_id != expected_id:
                raise ValueError(
                    "Syntax tree node IDs must be sequential integers starting at 1; "
                    f"expected {expected_id}, found {node_id}."
                )
