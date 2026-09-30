"""Lexical analyzer for SPL."""

from .diagnostics import Diagnostic, DiagnosticPhase, ExitCode, FrontendError
from .source import SourceFile
from .tokens import Token, TokenType, KEYWORDS, PUNCTUATION

# The syntax specification requires every token to end in blank_space.
# Keep the explicit override for investigating tutor interpretations.
ALLOW_EOF_AS_SEPARATOR: bool = False


def tokenize(source: SourceFile, allow_eof_terminator: bool | None = None) -> list[Token]:
    """Tokenize the source file and return all tokens including EOF.

    Args:
        source: The source file to tokenize.
        allow_eof_terminator: Whether EOF can terminate the final token.
            If None, uses the module-level ALLOW_EOF_AS_SEPARATOR setting.
    """
    if allow_eof_terminator is None:
        allow_eof_terminator = ALLOW_EOF_AS_SEPARATOR
    lexer = _Lexer(source, allow_eof_terminator)
    return lexer.tokenize()


class _Lexer:
    """Internal lexer state machine."""

    STRING_PUNCTUATION = frozenset(",.:-?!")

    def __init__(self, source: SourceFile, allow_eof_terminator: bool) -> None:
        self._source = source
        self._text = source.text
        self._path = source.path
        self._pos = 0
        self._line = 1
        self._column = 1
        self._tokens: list[Token] = []
        self._allow_eof_terminator = allow_eof_terminator

    def tokenize(self) -> list[Token]:
        """Process the entire source and return the token list."""
        while not self._at_end():
            self._skip_whitespace()
            if self._at_end():
                break
            self._scan_token()

        self._tokens.append(
            Token(TokenType.EOF, "", self._line, self._column, self._pos)
        )
        return self._tokens

    def _at_end(self) -> bool:
        return self._pos >= len(self._text)

    def _peek(self, offset: int = 0) -> str:
        """Look at a character without consuming it."""
        idx = self._pos + offset
        if idx >= len(self._text):
            return "\0"
        return self._text[idx]

    def _advance(self) -> str:
        """Consume and return the current character."""
        ch = self._text[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._column = 1
        elif ch == "\r":
            if self._peek() != "\n":
                self._line += 1
                self._column = 1
        else:
            self._column += 1
        return ch

    def _skip_whitespace(self) -> None:
        """Skip whitespace characters (space, CR, LF)."""
        while not self._at_end():
            ch = self._peek()
            if ch in " \r\n":
                self._advance()
            elif ch == "\t":
                self._error(
                    "LEX-TAB",
                    "tab character not allowed",
                    "use spaces for indentation and token separation",
                )
            else:
                break

    def _scan_token(self) -> None:
        """Scan the next token starting at current position."""
        start_pos = self._pos
        start_line = self._line
        start_col = self._column

        ch = self._peek()

        if ch == "$":
            self._error(
                "LEX-DOLLAR",
                "literal '$' not allowed in source",
                "'$' is only an end-of-file marker in the grammar, not valid input",
            )

        if ch == '"':
            self._scan_string(start_pos, start_line, start_col)
        elif ch == "#":
            self._scan_user_name(start_pos, start_line, start_col)
        elif ch == "-" or ch.isdigit():
            self._scan_number(start_pos, start_line, start_col)
        elif ch in PUNCTUATION:
            self._advance()
            lexeme = self._text[start_pos:self._pos]
            self._require_separator(lexeme, start_line, start_col)
            self._add_token(PUNCTUATION[ch], lexeme, start_line, start_col, start_pos)
        elif ch.isalpha():
            self._scan_keyword(start_pos, start_line, start_col)
        else:
            self._error(
                "LEX-UNKNOWN",
                f"unexpected character '{ch}'",
                "check for unsupported symbols or encoding issues",
            )

    def _scan_string(self, start_pos: int, start_line: int, start_col: int) -> None:
        """Scan a string literal."""
        self._advance()

        while not self._at_end() and self._peek() != '"':
            ch = self._peek()
            if ch in "\r\n":
                self._error(
                    "LEX-STRING-NEWLINE",
                    "newline inside string literal",
                    "strings must be on a single line",
                )
            if not self._is_valid_string_char(ch):
                self._error(
                    "LEX-STRING-CHAR",
                    f"invalid character '{ch}' in string",
                    "strings may only contain lowercase letters, digits, and ,.:-?!",
                )
            self._advance()

        if self._at_end():
            self._error_at(
                start_line,
                start_col,
                "LEX-STRING-UNTERMINATED",
                "unterminated string literal",
                "add a closing double quote",
            )

        self._advance()
        lexeme = self._text[start_pos:self._pos]
        self._require_separator(lexeme, start_line, start_col)
        self._add_token(TokenType.STRING, lexeme, start_line, start_col, start_pos)

    def _is_valid_string_char(self, ch: str) -> bool:
        """Check if a character is valid inside a string."""
        if ch.islower():
            return True
        if ch.isdigit():
            return True
        if ch in self.STRING_PUNCTUATION:
            return True
        return False

    def _scan_user_name(self, start_pos: int, start_line: int, start_col: int) -> None:
        """Scan a user-defined name starting with #."""
        self._advance()

        while not self._at_end():
            ch = self._peek()
            if ch.islower() or ch.isdigit():
                self._advance()
            elif ch.isupper():
                self._error_at(
                    start_line,
                    start_col,
                    "LEX-NAME-UPPER",
                    f"uppercase letter '{ch}' in user-defined name",
                    "user-defined names may only contain lowercase letters and digits after #",
                )
            elif ch in " \r\n":
                break
            elif ch == "\t":
                self._error(
                    "LEX-TAB",
                    "tab character not allowed",
                    "use spaces for indentation and token separation",
                )
            else:
                break

        lexeme = self._text[start_pos:self._pos]
        self._require_separator(lexeme, start_line, start_col)
        self._add_token(TokenType.USER_NAME, lexeme, start_line, start_col, start_pos)

    def _scan_number(self, start_pos: int, start_line: int, start_col: int) -> None:
        """Scan a numeric literal (integer or decimal)."""
        has_minus = False
        if self._peek() == "-":
            has_minus = True
            self._advance()

        if self._at_end() or not self._peek().isdigit():
            self._error_at(
                start_line,
                start_col,
                "LEX-NUM-INVALID",
                "expected digit after '-'",
                "a minus sign must be followed by digits",
            )

        integer_start = self._pos
        while not self._at_end() and self._peek().isdigit():
            self._advance()

        integer_part = self._text[integer_start:self._pos]
        has_decimal = False
        fractional_part = ""

        if not self._at_end() and self._peek() == ".":
            self._advance()
            has_decimal = True
            frac_start = self._pos

            if self._at_end() or not self._peek().isdigit():
                self._error_at(
                    start_line,
                    start_col,
                    "LEX-NUM-DECIMAL",
                    "expected digit after decimal point",
                    "decimals must have at least one fractional digit",
                )

            while not self._at_end() and self._peek().isdigit():
                self._advance()

            fractional_part = self._text[frac_start:self._pos]

        lexeme = self._text[start_pos:self._pos]
        self._require_separator(lexeme, start_line, start_col)

        self._validate_number(
            lexeme, integer_part, fractional_part, has_minus, has_decimal,
            start_line, start_col
        )

        self._add_token(TokenType.NUM, lexeme, start_line, start_col, start_pos)

    def _validate_number(
        self,
        lexeme: str,
        integer_part: str,
        fractional_part: str,
        has_minus: bool,
        has_decimal: bool,
        token_line: int,
        token_col: int,
    ) -> None:
        """Validate number format according to SPL rules."""
        if has_minus and integer_part == "0" and not has_decimal:
            self._error_at(
                token_line,
                token_col,
                "LEX-NUM-NEG-ZERO",
                "negative zero '-0' is not allowed",
                "use '0' for zero",
            )

        if len(integer_part) > 1 and integer_part[0] == "0":
            self._error_at(
                token_line,
                token_col,
                "LEX-NUM-LEADING-ZERO",
                f"leading zero in integer '{lexeme}'",
                "integers cannot have leading zeros unless the value is 0",
            )

        if has_decimal and fractional_part.endswith("0"):
            self._error_at(
                token_line,
                token_col,
                "LEX-NUM-TRAILING-ZERO",
                f"decimal '{lexeme}' ends with zero",
                "the last fractional digit must be 1-9",
            )

    def _scan_keyword(self, start_pos: int, start_line: int, start_col: int) -> None:
        """Scan a keyword."""
        while not self._at_end():
            ch = self._peek()
            if ch.isalpha():
                self._advance()
            else:
                break

        lexeme = self._text[start_pos:self._pos]

        if lexeme not in KEYWORDS:
            self._error_at(
                start_line,
                start_col,
                "LEX-UNKNOWN-WORD",
                f"unknown keyword '{lexeme}'",
                "check spelling or use # prefix for user-defined names",
            )

        self._require_separator(lexeme, start_line, start_col)
        self._add_token(KEYWORDS[lexeme], lexeme, start_line, start_col, start_pos)

    def _require_separator(self, lexeme: str, token_line: int, token_col: int) -> None:
        """Ensure the token is followed by blank_space (or permitted EOF)."""
        if self._at_end():
            if not self._allow_eof_terminator:
                self._error_at(
                    token_line,
                    token_col,
                    "LEX-NO-SEPARATOR",
                    f"missing whitespace after '{lexeme}'",
                    "every token must be followed by a space or newline",
                )
            return
        ch = self._peek()
        if ch not in " \r\n":
            if ch == "\t":
                self._error(
                    "LEX-TAB",
                    "tab character not allowed",
                    "use spaces for indentation and token separation",
                )
            self._error_at(
                token_line,
                token_col,
                "LEX-NO-SEPARATOR",
                f"missing whitespace after '{lexeme}'",
                "every token must be followed by a space or newline",
            )

    def _add_token(
        self,
        token_type: TokenType,
        lexeme: str,
        line: int,
        column: int,
        offset: int,
    ) -> None:
        """Add a token to the output list."""
        self._tokens.append(Token(token_type, lexeme, line, column, offset))

    def _error(self, code: str, message: str, hint: str) -> None:
        """Raise a lexical error at the current position."""
        self._error_at(self._line, self._column, code, message, hint)

    def _error_at(
        self, line: int, column: int, code: str, message: str, hint: str
    ) -> None:
        """Raise a lexical error at a specific position."""
        raise FrontendError(
            ExitCode.LEXICAL_ERROR,
            Diagnostic(
                phase=DiagnosticPhase.LEXER,
                code=code,
                message=message,
                path=self._path,
                line=line,
                column=column,
                hint=hint,
            ),
        )
