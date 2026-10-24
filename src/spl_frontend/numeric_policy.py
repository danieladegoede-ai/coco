"""Whole-program numeric restrictions and backend int/float mode selection.

This module scans the entire syntax tree for mod, div operators and decimal
NUM tokens to detect the two explicit numeric conflicts from Prac-Spec-2b:
1. If both mod AND div occur anywhere -> reject
2. If any mod occurs AND any decimal NUM exists -> reject

The scan distinguishes actual operators/NUM tokens from matching text inside
strings or comments.
"""

from __future__ import annotations

from dataclasses import dataclass

from spl_frontend.semantic_model import NumericMode
from spl_frontend.tree import NodeKind, SyntaxTree
from spl_frontend.tree_walkers import iter_preorder


@dataclass(frozen=True, slots=True)
class NumericScanResult:
    """Immutable result of the whole-program numeric scan."""
    has_mod: bool
    has_div: bool
    has_decimal: bool
    mode: NumericMode
    mod_node_id: int | None = None
    div_node_id: int | None = None
    decimal_node_id: int | None = None


class NumericPolicyError(ValueError):
    """Raised when a numeric policy violation is detected."""

    def __init__(
        self, code: str, message: str, *,
        node_id: int | None = None,
        related_node_id: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.node_id = node_id
        self.related_node_id = related_node_id

    def render(self) -> str:
        location = ""
        if self.node_id is not None:
            location = f"node[{self.node_id}]: "
        return f"{location}numeric[{self.code}]: {self.message}"


def scan_numeric_policy(tree: SyntaxTree) -> NumericScanResult:
    """Scan the entire tree for mod, div and decimal literals.

    This scans all nodes including those in uncalled/nested function bodies
    and return terms. Text inside strings or comments is ignored.

    Returns a NumericScanResult with the detected facts and selected mode.
    Raises NumericPolicyError if conflicts are detected.
    """
    has_mod = False
    has_div = False
    has_decimal = False
    mod_node_id: int | None = None
    div_node_id: int | None = None
    decimal_node_id: int | None = None

    for node in iter_preorder(tree):
        # Strings and comments are single quoted leaves. Inspect the actual
        # TERM production rather than searching text or walking ancestors.
        if node.kind is not NodeKind.INNER or node.contents != "TERM" or not node.child_ids:
            continue
        first = tree.get_node(node.child_ids[0])
        if first.kind is not NodeKind.LEAF:
            continue
        if first.contents == "mod" and not has_mod:
            has_mod, mod_node_id = True, first.node_id
        elif first.contents == "div" and not has_div:
            has_div, div_node_id = True, first.node_id
        elif (len(node.child_ids) == 1 and "." in first.contents
              and first.contents.lstrip("-")[:1].isdigit() and not has_decimal):
            has_decimal, decimal_node_id = True, first.node_id

    if has_mod and has_div:
        raise NumericPolicyError(
            "FLOAT-INT-CONFLICT",
            "A float-integer-conflict might perhaps be possible",
            node_id=mod_node_id,
            related_node_id=div_node_id,
        )

    if has_mod and has_decimal:
        raise NumericPolicyError(
            "DECIMAL-WITH-MOD",
            "Decimal numbers cannot be used with mod operator",
            node_id=decimal_node_id,
            related_node_id=mod_node_id,
        )

    if has_div or has_decimal:
        mode = NumericMode.FLOAT
    else:
        mode = NumericMode.INTEGER

    return NumericScanResult(
        has_mod=has_mod,
        has_div=has_div,
        has_decimal=has_decimal,
        mode=mode,
        mod_node_id=mod_node_id,
        div_node_id=div_node_id,
        decimal_node_id=decimal_node_id,
    )
