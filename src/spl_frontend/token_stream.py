"""Approved list-backed token source used by the parser."""

from __future__ import annotations

from collections.abc import Sequence

from spl_frontend.tokens import Token, TokenType


class TokenStream:
    """Read an immutable token sequence with deterministic lookahead."""

    def __init__(self, tokens: Sequence[Token]) -> None:
        self._tokens = tuple(tokens)
        self._position = 0
        self._validate_tokens()

    @property
    def position(self) -> int:
        return self._position

    def peek(self, distance: int = 0) -> Token:
        if distance < 0:
            raise ValueError("Lookahead distance cannot be negative.")
        index = min(self._position + distance, len(self._tokens) - 1)
        return self._tokens[index]

    def consume(self) -> Token:
        token = self.peek()
        if token.token_type is not TokenType.EOF:
            self._position += 1
        return token

    def at_end(self) -> bool:
        return self.peek().token_type is TokenType.EOF

    def _validate_tokens(self) -> None:
        if not self._tokens:
            raise ValueError("A token stream requires a final EOF token.")
        if self._tokens[-1].token_type is not TokenType.EOF:
            raise ValueError("The final token must be EOF.")
        if any(token.token_type is TokenType.EOF for token in self._tokens[:-1]):
            raise ValueError("EOF may appear only as the final token.")
