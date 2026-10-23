"""Match source-order leaves to lexer tokens, never to a spelling search."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from spl_frontend.semantic_model import FoundationError, SourceSpan
from spl_frontend.tokens import Token, TokenType
from spl_frontend.tree import NodeKind, SyntaxTree
from spl_frontend.tree_walkers import iter_leaves, iter_postorder


@dataclass(frozen=True, slots=True)
class SourceMap:
    path: Path
    source_location_by_node: Mapping[int, SourceSpan]

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            raise ValueError("Source map path must be a Path.")
        spans = dict(self.source_location_by_node)
        for node_id, span in spans.items():
            if (
                type(node_id) is not int or node_id < 1
                or not isinstance(span, SourceSpan) or span.path != self.path
            ):
                raise ValueError("Invalid source-map node/span/path.")
        object.__setattr__(self, "source_location_by_node", MappingProxyType(spans))

    def span_for(self, node_id: int) -> SourceSpan | None:
        if type(node_id) is not int or node_id < 1:
            raise ValueError("Source map node ID must be a positive integer.")
        return self.source_location_by_node.get(node_id)


def build_source_map(tree: SyntaxTree, tokens: Sequence[Token], path: Path) -> SourceMap:
    """Return leaf and enclosing-node spans after exact token alignment.

    Empty productions have no source span. Without original tokens, retain
    node IDs and use an empty SourceMap; XML alone has no SPL line numbers.
    """
    try:
        tree.validate()
    except ValueError as exc:
        raise FoundationError("MAP-TREE", str(exc), path=path) from exc
    if not tokens or any(not isinstance(t, Token) for t in tokens):
        raise FoundationError("MAP-TOKENS", "Expected a token sequence ending in EOF.", path=path)
    if tokens[-1].token_type is not TokenType.EOF or any(t.token_type is TokenType.EOF for t in tokens[:-1]):
        raise FoundationError("MAP-EOF", "Expected exactly one final internal EOF token.", path=path)
    leaves = list(iter_leaves(tree))
    actual = list(tokens[:-1])
    if len(leaves) != len(actual):
        raise FoundationError(
            "MAP-COUNT",
            f"Tree has {len(leaves)} leaves but source has {len(actual)} tokens.",
            path=path,
        )
    spans: dict[int, SourceSpan] = {}
    previous_end = 0
    previous_position = (1, 1)
    for leaf, token in zip(leaves, actual):
        if not token.lexeme or "\n" in token.lexeme or "\r" in token.lexeme:
            raise FoundationError(
                "MAP-TOKENS", "An SPL token must be nonempty and on one source line.",
                path=path, node_id=leaf.node_id,
            )
        try:
            span = SourceSpan(path, token.line, token.column, token.offset, token.line,
                              token.column + len(token.lexeme), token.offset + len(token.lexeme))
        except ValueError as exc:
            raise FoundationError("MAP-TOKENS", str(exc), path=path, node_id=leaf.node_id) from exc
        if token.offset < previous_end or (token.line, token.column) < previous_position:
            raise FoundationError(
                "MAP-ORDER", "Source token locations overlap or are out of order.",
                span=span, node_id=leaf.node_id,
            )
        if leaf.contents != token.lexeme:
            raise FoundationError(
                "MAP-LEXEME",
                f"Tree leaf {leaf.contents!r} does not match source token {token.lexeme!r}.",
                span=span, node_id=leaf.node_id,
            )
        spans[leaf.node_id] = span
        previous_end = span.end_offset
        previous_position = (span.end_line, span.end_column)
    eof = tokens[-1]
    try:
        SourceSpan(path, eof.line, eof.column, eof.offset,
                   eof.line, eof.column, eof.offset)
    except ValueError as exc:
        raise FoundationError("MAP-EOF", str(exc), path=path) from exc
    if eof.offset < previous_end or (eof.line, eof.column) < previous_position:
        raise FoundationError("MAP-EOF", "EOF precedes the last source token.", path=path)
    for node in iter_postorder(tree):
        if node.kind is NodeKind.LEAF:
            continue
        children = [spans[c] for c in node.child_ids if c in spans]
        if children:
            first, last = children[0], children[-1]
            spans[node.node_id] = SourceSpan(path, first.line, first.column, first.offset,
                                             last.end_line, last.end_column, last.end_offset)
    return SourceMap(path, spans)
