"""Tests for the TokenStream class."""

import unittest

from spl_frontend.tokens import Token, TokenType
from spl_frontend.token_stream import TokenStream


def make_token(tt: TokenType, lexeme: str = "") -> Token:
    """Create a token for testing."""
    return Token(tt, lexeme, 1, 1, 0)


class TestTokenStreamInit(unittest.TestCase):
    """Tests for TokenStream initialization."""

    def test_valid_sequence(self):
        tokens = [make_token(TokenType.PRINT, "print"), make_token(TokenType.EOF)]
        stream = TokenStream(tokens)
        self.assertIsNotNone(stream)

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            TokenStream([])

    def test_no_eof_rejected(self):
        tokens = [make_token(TokenType.PRINT, "print")]
        with self.assertRaises(ValueError):
            TokenStream(tokens)


class TestPeek(unittest.TestCase):
    """Tests for the peek method."""

    def test_peek_current(self):
        tokens = [
            make_token(TokenType.PRINT, "print"),
            make_token(TokenType.NOP, "nop"),
            make_token(TokenType.EOF),
        ]
        stream = TokenStream(tokens)
        self.assertEqual(stream.peek().token_type, TokenType.PRINT)

    def test_peek_ahead(self):
        tokens = [
            make_token(TokenType.PRINT, "print"),
            make_token(TokenType.NOP, "nop"),
            make_token(TokenType.EOF),
        ]
        stream = TokenStream(tokens)
        self.assertEqual(stream.peek(1).token_type, TokenType.NOP)

    def test_peek_does_not_advance(self):
        tokens = [
            make_token(TokenType.PRINT, "print"),
            make_token(TokenType.EOF),
        ]
        stream = TokenStream(tokens)
        stream.peek()
        stream.peek()
        stream.peek()
        self.assertEqual(stream.position, 0)

    def test_peek_past_end_returns_eof(self):
        tokens = [
            make_token(TokenType.PRINT, "print"),
            make_token(TokenType.EOF),
        ]
        stream = TokenStream(tokens)
        self.assertEqual(stream.peek(100).token_type, TokenType.EOF)


class TestConsume(unittest.TestCase):
    """Tests for the consume method."""

    def test_consume_returns_current(self):
        tokens = [
            make_token(TokenType.PRINT, "print"),
            make_token(TokenType.EOF),
        ]
        stream = TokenStream(tokens)
        token = stream.consume()
        self.assertEqual(token.token_type, TokenType.PRINT)

    def test_consume_advances(self):
        tokens = [
            make_token(TokenType.PRINT, "print"),
            make_token(TokenType.NOP, "nop"),
            make_token(TokenType.EOF),
        ]
        stream = TokenStream(tokens)
        stream.consume()
        self.assertEqual(stream.peek().token_type, TokenType.NOP)

    def test_consume_sequence(self):
        tokens = [
            make_token(TokenType.PRINT, "print"),
            make_token(TokenType.NOP, "nop"),
            make_token(TokenType.EOF),
        ]
        stream = TokenStream(tokens)
        t1 = stream.consume()
        t2 = stream.consume()
        t3 = stream.consume()
        self.assertEqual(t1.token_type, TokenType.PRINT)
        self.assertEqual(t2.token_type, TokenType.NOP)
        self.assertEqual(t3.token_type, TokenType.EOF)

    def test_consume_eof_repeatedly(self):
        tokens = [make_token(TokenType.EOF)]
        stream = TokenStream(tokens)
        t1 = stream.consume()
        t2 = stream.consume()
        t3 = stream.consume()
        self.assertEqual(t1.token_type, TokenType.EOF)
        self.assertEqual(t2.token_type, TokenType.EOF)
        self.assertEqual(t3.token_type, TokenType.EOF)


class TestAtEnd(unittest.TestCase):
    """Tests for the at_end method."""

    def test_not_at_end(self):
        tokens = [
            make_token(TokenType.PRINT, "print"),
            make_token(TokenType.EOF),
        ]
        stream = TokenStream(tokens)
        self.assertFalse(stream.at_end())

    def test_at_end_after_consuming_all(self):
        tokens = [
            make_token(TokenType.PRINT, "print"),
            make_token(TokenType.EOF),
        ]
        stream = TokenStream(tokens)
        stream.consume()
        self.assertTrue(stream.at_end())

    def test_eof_only(self):
        tokens = [make_token(TokenType.EOF)]
        stream = TokenStream(tokens)
        self.assertTrue(stream.at_end())


class TestParserIntegration(unittest.TestCase):
    """Tests demonstrating parser-like usage patterns."""

    def test_lookahead_pattern(self):
        tokens = [
            make_token(TokenType.USER_NAME, "#x"),
            make_token(TokenType.ASSIGN, "="),
            make_token(TokenType.NUM, "42"),
            make_token(TokenType.EOF),
        ]
        stream = TokenStream(tokens)

        # Parser sees a name, needs to check if assignment or call
        name = stream.peek()
        self.assertEqual(name.token_type, TokenType.USER_NAME)

        # Lookahead to decide
        next_token = stream.peek(1)
        self.assertEqual(next_token.token_type, TokenType.ASSIGN)

        # It is assignment, consume all three
        stream.consume()  # name
        stream.consume()  # =
        stream.consume()  # value

        self.assertTrue(stream.at_end())

    def test_function_call_lookahead(self):
        tokens = [
            make_token(TokenType.USER_NAME, "#func"),
            make_token(TokenType.LPAREN, "("),
            make_token(TokenType.RPAREN, ")"),
            make_token(TokenType.EOF),
        ]
        stream = TokenStream(tokens)

        name = stream.peek()
        next_token = stream.peek(1)

        # ( means function call, not assignment
        self.assertEqual(next_token.token_type, TokenType.LPAREN)


if __name__ == "__main__":
    unittest.main()
