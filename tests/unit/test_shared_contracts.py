from __future__ import annotations

import unittest
from pathlib import Path

from spl_frontend.cli_contract import CliRequest
from spl_frontend.diagnostics import Diagnostic, DiagnosticPhase
from spl_frontend.token_stream import TokenStream
from spl_frontend.tokens import Token, TokenType
from spl_frontend.tree import NodeKind, TreeNode


def token(token_type: TokenType, lexeme: str, offset: int = 0) -> Token:
    return Token(token_type, lexeme, 1, offset + 1, offset)


class TokenContractTests(unittest.TestCase):
    def test_token_keeps_type_lexeme_and_position(self) -> None:
        value = token(TokenType.USER_NAME, "#value", 3)
        self.assertEqual(value.token_type, TokenType.USER_NAME)
        self.assertEqual(value.lexeme, "#value")
        self.assertEqual((value.line, value.column, value.offset), (1, 4, 3))

    def test_eof_must_have_empty_lexeme(self) -> None:
        with self.assertRaises(ValueError):
            token(TokenType.EOF, "$")


class TokenStreamContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.name = token(TokenType.USER_NAME, "#x")
        self.assign = token(TokenType.ASSIGN, "=", 3)
        self.eof = token(TokenType.EOF, "", 4)
        self.stream = TokenStream([self.name, self.assign, self.eof])

    def test_peek_does_not_consume(self) -> None:
        self.assertIs(self.stream.peek(), self.name)
        self.assertIs(self.stream.peek(1), self.assign)
        self.assertEqual(self.stream.position, 0)

    def test_consume_stops_at_eof(self) -> None:
        self.assertIs(self.stream.consume(), self.name)
        self.assertIs(self.stream.consume(), self.assign)
        self.assertTrue(self.stream.at_end())
        self.assertIs(self.stream.consume(), self.eof)
        self.assertTrue(self.stream.at_end())

    def test_requires_one_final_eof(self) -> None:
        with self.assertRaises(ValueError):
            TokenStream([])
        with self.assertRaises(ValueError):
            TokenStream([self.name])
        with self.assertRaises(ValueError):
            TokenStream([self.eof, self.name, self.eof])


class TreeTypeContractTests(unittest.TestCase):
    def test_root_and_leaf_invariants(self) -> None:
        root = TreeNode(1, NodeKind.ROOT, "SPL_PROG", None)
        leaf = TreeNode(2, NodeKind.LEAF, "nop", root.node_id)
        self.assertEqual(root.parent_id, None)
        self.assertEqual(leaf.parent_id, root.node_id)

    def test_leaf_cannot_have_children(self) -> None:
        with self.assertRaises(ValueError):
            TreeNode(2, NodeKind.LEAF, "nop", 1, [3])


class DiagnosticContractTests(unittest.TestCase):
    def test_render_contains_location_phase_code_and_hint(self) -> None:
        diagnostic = Diagnostic(
            phase=DiagnosticPhase.SYNTAX,
            code="SYN-EXPECTED",
            message="expected ';' but found 'print'",
            path=Path("SPL.txt"),
            line=4,
            column=12,
            hint="every instruction in ALGO must end with ';'",
        )
        self.assertEqual(
            diagnostic.render(),
            "SPL.txt:4:12: syntax[SYN-EXPECTED]: "
            "expected ';' but found 'print'\n"
            "hint: every instruction in ALGO must end with ';'",
        )


class CliContractTests(unittest.TestCase):
    def test_default_and_custom_paths(self) -> None:
        default = CliRequest()
        custom = CliRequest(Path("case.spl"), Path("result.xml"))
        self.assertEqual(default.input_path, Path("SPL.txt"))
        self.assertEqual(default.output_path, Path("tree.xml"))
        self.assertEqual(custom.input_path, Path("case.spl"))
        self.assertEqual(custom.output_path, Path("result.xml"))


if __name__ == "__main__":
    unittest.main()
