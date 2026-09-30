"""Tests for the SPL lexer."""

import unittest
from pathlib import Path

from spl_frontend.source import SourceFile
from spl_frontend.lexer import tokenize
from spl_frontend.tokens import Token, TokenType
from spl_frontend.diagnostics import FrontendError


def make_source(text: str) -> SourceFile:
    """Create a SourceFile from a string for testing."""
    return SourceFile(path=Path("test.spl"), text=text)


class TestKeywords(unittest.TestCase):
    """Tests for keyword recognition."""

    def test_all_keywords(self):
        keywords = [
            ("void ", TokenType.VOID),
            ("num ", TokenType.NUM_TYPE),
            ("return ", TokenType.RETURN),
            ("print ", TokenType.PRINT),
            ("nop ", TokenType.NOP),
            ("comment ", TokenType.COMMENT),
            ("if ", TokenType.IF),
            ("then ", TokenType.THEN),
            ("else ", TokenType.ELSE),
            ("while ", TokenType.WHILE),
            ("until ", TokenType.UNTIL),
            ("do ", TokenType.DO),
            ("not ", TokenType.NOT),
            ("and ", TokenType.AND),
            ("or ", TokenType.OR),
            ("eq ", TokenType.EQ),
            ("larger ", TokenType.LARGER),
            ("lesser ", TokenType.LESSER),
            ("mod ", TokenType.MOD),
            ("add ", TokenType.ADD),
            ("sub ", TokenType.SUB),
            ("mul ", TokenType.MUL),
            ("div ", TokenType.DIV),
            ("neg ", TokenType.NEG),
        ]
        for text, expected_type in keywords:
            with self.subTest(text=text.strip()):
                tokens = tokenize(make_source(text))
                self.assertEqual(len(tokens), 2)
                self.assertEqual(tokens[0].token_type, expected_type)
                self.assertEqual(tokens[0].lexeme, text.strip())
                self.assertEqual(tokens[1].token_type, TokenType.EOF)


class TestPunctuation(unittest.TestCase):
    """Tests for punctuation tokens."""

    def test_all_punctuation(self):
        punctuation = [
            ("( ", TokenType.LPAREN),
            (") ", TokenType.RPAREN),
            ("{ ", TokenType.LBRACE),
            ("} ", TokenType.RBRACE),
            (": ", TokenType.COLON),
            ("; ", TokenType.SEMICOLON),
            ("= ", TokenType.ASSIGN),
        ]
        for text, expected_type in punctuation:
            with self.subTest(text=text.strip()):
                tokens = tokenize(make_source(text))
                self.assertEqual(len(tokens), 2)
                self.assertEqual(tokens[0].token_type, expected_type)


class TestNumbers(unittest.TestCase):
    """Tests for NUM tokens."""

    def test_zero(self):
        tokens = tokenize(make_source("0 "))
        self.assertEqual(tokens[0].token_type, TokenType.NUM)
        self.assertEqual(tokens[0].lexeme, "0")

    def test_positive_integer(self):
        tokens = tokenize(make_source("42 "))
        self.assertEqual(tokens[0].token_type, TokenType.NUM)
        self.assertEqual(tokens[0].lexeme, "42")

    def test_negative_integer(self):
        tokens = tokenize(make_source("-7 "))
        self.assertEqual(tokens[0].token_type, TokenType.NUM)
        self.assertEqual(tokens[0].lexeme, "-7")

    def test_large_integer(self):
        tokens = tokenize(make_source("123456789 "))
        self.assertEqual(tokens[0].lexeme, "123456789")

    def test_decimal_positive(self):
        tokens = tokenize(make_source("3.14 "))
        self.assertEqual(tokens[0].token_type, TokenType.NUM)
        self.assertEqual(tokens[0].lexeme, "3.14")

    def test_decimal_negative(self):
        tokens = tokenize(make_source("-2.5 "))
        self.assertEqual(tokens[0].lexeme, "-2.5")

    def test_decimal_ending_nonzero(self):
        tokens = tokenize(make_source("1.001 "))
        self.assertEqual(tokens[0].lexeme, "1.001")

    def test_zero_decimal(self):
        tokens = tokenize(make_source("0.5 "))
        self.assertEqual(tokens[0].lexeme, "0.5")

    def test_negative_zero_rejected(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("-0 "))
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-NUM-NEG-ZERO")

    def test_leading_zero_rejected(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("007 "))
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-NUM-LEADING-ZERO")

    def test_decimal_trailing_zero_rejected(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("1.50 "))
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-NUM-TRAILING-ZERO")

    def test_decimal_no_fraction_rejected(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("5. "))
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-NUM-DECIMAL")

    def test_minus_alone_rejected(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("- "))
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-NUM-INVALID")


class TestUserDefinedNames(unittest.TestCase):
    """Tests for USER_NAME tokens."""

    def test_simple_name(self):
        tokens = tokenize(make_source("#var "))
        self.assertEqual(tokens[0].token_type, TokenType.USER_NAME)
        self.assertEqual(tokens[0].lexeme, "#var")

    def test_name_with_digits(self):
        tokens = tokenize(make_source("#x1y2z3 "))
        self.assertEqual(tokens[0].lexeme, "#x1y2z3")

    def test_long_name(self):
        tokens = tokenize(make_source("#verylongvariablename123 "))
        self.assertEqual(tokens[0].lexeme, "#verylongvariablename123")

    def test_hash_alone(self):
        tokens = tokenize(make_source("# "))
        self.assertEqual(tokens[0].token_type, TokenType.USER_NAME)
        self.assertEqual(tokens[0].lexeme, "#")

    def test_uppercase_rejected(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("#Var "))
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-NAME-UPPER")


class TestStrings(unittest.TestCase):
    """Tests for STRING tokens."""

    def test_empty_string(self):
        tokens = tokenize(make_source('"" '))
        self.assertEqual(tokens[0].token_type, TokenType.STRING)
        self.assertEqual(tokens[0].lexeme, '""')

    def test_simple_string(self):
        tokens = tokenize(make_source('"hello" '))
        self.assertEqual(tokens[0].lexeme, '"hello"')

    def test_string_with_digits(self):
        tokens = tokenize(make_source('"abc123" '))
        self.assertEqual(tokens[0].lexeme, '"abc123"')

    def test_string_with_punctuation(self):
        tokens = tokenize(make_source('"hello,world." '))
        self.assertEqual(tokens[0].lexeme, '"hello,world."')

    def test_string_all_allowed_punctuation(self):
        tokens = tokenize(make_source('",.:-?!" '))
        self.assertEqual(tokens[0].lexeme, '",.:-?!"')

    def test_unterminated_string_rejected(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source('"hello'))
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-STRING-UNTERMINATED")

    def test_string_with_space_rejected(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source('"hello world" '))
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-STRING-CHAR")

    def test_string_with_uppercase_rejected(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source('"Hello" '))
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-STRING-CHAR")

    def test_string_newline_rejected(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source('"hello\nworld" '))
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-STRING-NEWLINE")


class TestWhitespace(unittest.TestCase):
    """Tests for whitespace handling."""

    def test_space_separator(self):
        tokens = tokenize(make_source("print nop "))
        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[0].token_type, TokenType.PRINT)
        self.assertEqual(tokens[1].token_type, TokenType.NOP)

    def test_newline_separator(self):
        tokens = tokenize(make_source("print\nnop\n"))
        self.assertEqual(len(tokens), 3)

    def test_crlf_separator(self):
        tokens = tokenize(make_source("print\r\nnop\r\n"))
        self.assertEqual(len(tokens), 3)

    def test_cr_separator(self):
        tokens = tokenize(make_source("print\rnop\r"))
        self.assertEqual(len(tokens), 3)

    def test_tab_rejected(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("print\tnop "))
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-TAB")

    def test_missing_separator_rejected(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("printnop "))
        self.assertIn("unknown keyword", ctx.exception.diagnostic.message)

    def test_number_letter_no_separator(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("123abc "))
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-NO-SEPARATOR")


class TestSpecialCases(unittest.TestCase):
    """Tests for special cases and edge conditions."""

    def test_empty_input(self):
        tokens = tokenize(make_source(""))
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].token_type, TokenType.EOF)

    def test_whitespace_only(self):
        tokens = tokenize(make_source("   \n\n  "))
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].token_type, TokenType.EOF)

    def test_dollar_rejected(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("$ "))
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-DOLLAR")

    def test_unknown_symbol_rejected(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("@ "))
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-UNKNOWN")

    def test_default_requires_blank_space_after_final_token(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("print"))
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-NO-SEPARATOR")


class TestPositionTracking(unittest.TestCase):
    """Tests for line, column, and offset tracking."""

    def test_first_token_position(self):
        tokens = tokenize(make_source("print "))
        self.assertEqual(tokens[0].line, 1)
        self.assertEqual(tokens[0].column, 1)
        self.assertEqual(tokens[0].offset, 0)

    def test_second_token_position(self):
        tokens = tokenize(make_source("print nop "))
        self.assertEqual(tokens[1].line, 1)
        self.assertEqual(tokens[1].column, 7)
        self.assertEqual(tokens[1].offset, 6)

    def test_newline_position(self):
        tokens = tokenize(make_source("print\nnop "))
        self.assertEqual(tokens[1].line, 2)
        self.assertEqual(tokens[1].column, 1)

    def test_crlf_position(self):
        tokens = tokenize(make_source("print\r\nnop "))
        self.assertEqual(tokens[1].line, 2)
        self.assertEqual(tokens[1].column, 1)

    def test_multiple_lines_position(self):
        tokens = tokenize(make_source("print\nnop\nif "))
        self.assertEqual(tokens[2].line, 3)
        self.assertEqual(tokens[2].column, 1)

    def test_error_position_after_newline(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("print\n$ "))
        diag = ctx.exception.diagnostic
        self.assertEqual(diag.line, 2)
        self.assertEqual(diag.column, 1)


class TestMultipleTokens(unittest.TestCase):
    """Tests for sequences of multiple tokens."""

    def test_simple_sequence(self):
        tokens = tokenize(make_source("print ( #x ) "))
        types = [t.token_type for t in tokens]
        self.assertEqual(types, [
            TokenType.PRINT,
            TokenType.LPAREN,
            TokenType.USER_NAME,
            TokenType.RPAREN,
            TokenType.EOF,
        ])

    def test_assignment_sequence(self):
        tokens = tokenize(make_source("#x = 42 "))
        types = [t.token_type for t in tokens]
        self.assertEqual(types, [
            TokenType.USER_NAME,
            TokenType.ASSIGN,
            TokenType.NUM,
            TokenType.EOF,
        ])

    def test_function_header_sequence(self):
        tokens = tokenize(make_source("void #func ( #a #b ) { "))
        types = [t.token_type for t in tokens]
        self.assertEqual(types, [
            TokenType.VOID,
            TokenType.USER_NAME,
            TokenType.LPAREN,
            TokenType.USER_NAME,
            TokenType.USER_NAME,
            TokenType.RPAREN,
            TokenType.LBRACE,
            TokenType.EOF,
        ])


class TestEofTerminatorPolicy(unittest.TestCase):
    """Tests for configurable EOF-as-separator policy."""

    def test_eof_allowed_as_terminator(self):
        tokens = tokenize(make_source("print"), allow_eof_terminator=True)
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].token_type, TokenType.PRINT)

    def test_eof_disallowed_as_terminator(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("print"), allow_eof_terminator=False)
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-NO-SEPARATOR")

    def test_eof_allowed_number(self):
        tokens = tokenize(make_source("42"), allow_eof_terminator=True)
        self.assertEqual(tokens[0].lexeme, "42")

    def test_eof_disallowed_number(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("42"), allow_eof_terminator=False)
        self.assertEqual(ctx.exception.diagnostic.code, "LEX-NO-SEPARATOR")

    def test_trailing_space_works_either_way(self):
        tokens_allow = tokenize(make_source("print "), allow_eof_terminator=True)
        tokens_disallow = tokenize(make_source("print "), allow_eof_terminator=False)
        self.assertEqual(len(tokens_allow), 2)
        self.assertEqual(len(tokens_disallow), 2)


class TestMalformedTokenPositions(unittest.TestCase):
    """Tests that malformed token errors point to token start, not end."""

    def test_negative_zero_position(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("-0 "))
        diag = ctx.exception.diagnostic
        self.assertEqual(diag.line, 1)
        self.assertEqual(diag.column, 1)

    def test_leading_zero_position(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("00 "))
        diag = ctx.exception.diagnostic
        self.assertEqual(diag.line, 1)
        self.assertEqual(diag.column, 1)

    def test_trailing_zero_decimal_position(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("1.50 "))
        diag = ctx.exception.diagnostic
        self.assertEqual(diag.line, 1)
        self.assertEqual(diag.column, 1)

    def test_unknown_keyword_position(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("bogus "))
        diag = ctx.exception.diagnostic
        self.assertEqual(diag.line, 1)
        self.assertEqual(diag.column, 1)

    def test_malformed_number_on_line_two(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("print\n-0 "))
        diag = ctx.exception.diagnostic
        self.assertEqual(diag.line, 2)
        self.assertEqual(diag.column, 1)

    def test_malformed_number_after_token(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("print 00 "))
        diag = ctx.exception.diagnostic
        self.assertEqual(diag.line, 1)
        self.assertEqual(diag.column, 7)

    def test_uppercase_name_position(self):
        with self.assertRaises(FrontendError) as ctx:
            tokenize(make_source("#varX "))
        diag = ctx.exception.diagnostic
        self.assertEqual(diag.line, 1)
        self.assertEqual(diag.column, 1)


if __name__ == "__main__":
    unittest.main()
