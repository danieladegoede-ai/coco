"""Iterative, source-order access to the existing concrete syntax tree.

Call tree.validate() at the phase boundary. Walkers additionally reject local
shape errors/repeated nodes rather than looping on damaged input. These
helpers do not replace the parser or perform name/type analysis.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import re

from spl_frontend.semantic_model import FoundationError
from spl_frontend.tree import NodeKind, SyntaxTree, TreeNode


def _node(tree: SyntaxTree, node_id: int) -> TreeNode:
    try:
        return tree.get_node(node_id)
    except ValueError as exc:
        raise FoundationError("TREE-NODE", str(exc), node_id=node_id) from exc


def iter_preorder(tree: SyntaxTree, node_id: int | None = None) -> Iterator[TreeNode]:
    if node_id is None:
        if tree.root is None:
            raise FoundationError("TREE-ROOT", "Syntax tree has no root.")
        node_id = tree.root.node_id
    pending = [node_id]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            raise FoundationError("TREE-REPEATED", "Cycle or repeated child reference.", node_id=current)
        seen.add(current)
        node = _node(tree, current)
        yield node
        pending.extend(reversed(node.child_ids))


def iter_postorder(tree: SyntaxTree, node_id: int | None = None) -> Iterator[TreeNode]:
    if node_id is None:
        if tree.root is None:
            raise FoundationError("TREE-ROOT", "Syntax tree has no root.")
        node_id = tree.root.node_id
    pending = [(node_id, False)]
    seen: set[int] = set()
    while pending:
        current, visited = pending.pop()
        node = _node(tree, current)
        if visited:
            yield node
            continue
        if current in seen:
            raise FoundationError("TREE-REPEATED", "Cycle or repeated child reference.", node_id=current)
        seen.add(current)
        pending.append((current, True))
        pending.extend((child, False) for child in reversed(node.child_ids))


def iter_leaves(tree: SyntaxTree, node_id: int | None = None) -> Iterator[TreeNode]:
    for node in iter_preorder(tree, node_id):
        if node.kind is NodeKind.LEAF:
            yield node


def _require(node: TreeNode, kind: NodeKind, contents: str | None = None) -> None:
    if node.kind is not kind or (contents is not None and node.contents != contents):
        raise FoundationError(
            "TREE-SHAPE",
            f"Expected {kind.value} {contents or 'node'}, found {node.contents!r}.",
            node_id=node.node_id,
        )


def iter_list_items(tree: SyntaxTree, node_id: int) -> Iterator[TreeNode]:
    """Flatten exactly V_DECL, F_DECL, INPUT or ALGO, excluding the null tail."""
    node = _node(tree, node_id)
    label = node.contents
    heads = {"V_DECL": (NodeKind.LEAF, None), "F_DECL": (NodeKind.INNER, "F_TYPE"),
             "INPUT": (NodeKind.INNER, "TERM"), "ALGO": (NodeKind.INNER, "INSTR")}
    if label not in heads:
        raise FoundationError("TREE-LIST", f"{label!r} is not an SPL list production.", node_id=node_id)
    seen: set[int] = set()
    while True:
        _require(node, NodeKind.INNER, label)
        if node.node_id in seen:
            raise FoundationError("TREE-REPEATED", "Cycle in list tail.", node_id=node.node_id)
        seen.add(node.node_id)
        if not node.child_ids:
            return
        expected = 3 if label == "ALGO" else 2
        if len(node.child_ids) != expected:
            raise FoundationError(
                "TREE-SHAPE", f"{label} requires {expected} children or a nullable tail.",
                node_id=node.node_id,
            )
        children = [_node(tree, child) for child in node.child_ids]
        head, tail = children[0], children[-1]
        _require(head, *heads[label])
        if label == "V_DECL" and not re.fullmatch(r"#[a-z0-9]*", head.contents):
            raise FoundationError("TREE-SHAPE", "V_DECL head must be a user-defined name.", node_id=head.node_id)
        if label == "ALGO":
            _require(children[1], NodeKind.LEAF, ";")
        _require(tail, NodeKind.INNER, label)
        yield head
        node = tail


@dataclass(frozen=True, slots=True)
class ProgramParts:
    variables: TreeNode
    functions: TreeNode
    algorithm: TreeNode


def program_parts(tree: SyntaxTree, node_id: int) -> ProgramParts:
    node = _node(tree, node_id)
    _require(node, NodeKind.INNER, "P")
    if len(node.child_ids) != 5:
        raise FoundationError("TREE-SHAPE", "P requires V_DECL : F_DECL : ALGO.", node_id=node_id)
    children = [_node(tree, child) for child in node.child_ids]
    for index, label in enumerate(["V_DECL", ":", "F_DECL", ":", "ALGO"]):
        kind = NodeKind.LEAF if label == ":" else NodeKind.INNER
        _require(children[index], kind, label)
    return ProgramParts(children[0], children[2], children[4])


@dataclass(frozen=True, slots=True)
class FunctionParts:
    return_keyword: str
    name: TreeNode
    parameters: TreeNode
    body: TreeNode
    return_term: TreeNode | None


def function_parts(tree: SyntaxTree, node_id: int) -> FunctionParts:
    node = _node(tree, node_id)
    _require(node, NodeKind.INNER, "F_TYPE")
    children = [_node(tree, child) for child in node.child_ids]
    if not children or children[0].contents not in {"void", "num"}:
        raise FoundationError("TREE-SHAPE", "Function must start with void or num.", node_id=node_id)
    numeric = children[0].contents == "num"
    labels = [children[0].contents, None, "(", "V_DECL", ")", "{", "P", "return"]
    labels += ["(", "TERM", ")", "}"] if numeric else ["}"]
    if len(children) != len(labels):
        raise FoundationError("TREE-SHAPE", "Function has an invalid declaration/return shape.", node_id=node_id)
    for child, label in zip(children, labels):
        kind = NodeKind.INNER if label in {"V_DECL", "P", "TERM"} else NodeKind.LEAF
        _require(child, kind, label)
    if not re.fullmatch(r"#[a-z0-9]*", children[1].contents):
        raise FoundationError(
            "TREE-SHAPE", "Function name must be a user-defined name.",
            node_id=children[1].node_id,
        )
    return FunctionParts(
        children[0].contents, children[1], children[3], children[6],
        children[9] if numeric else None,
    )
