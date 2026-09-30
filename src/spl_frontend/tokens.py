"""Approved token representation shared by the lexer and parser."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TokenType(str, Enum):
    """Every lexical category, keyword, punctuation token and internal EOF."""

    EOF = "EOF"
    NUM = "NUM"
    USER_NAME = "USER-DEFINED-NAME"
    STRING = "STRING"

    VOID = "void"
    NUM_TYPE = "num"
    RETURN = "return"
    PRINT = "print"
    NOP = "nop"
    COMMENT = "comment"
    IF = "if"
    THEN = "then"
    ELSE = "else"
    WHILE = "while"
    UNTIL = "until"
    DO = "do"
    NOT = "not"
    AND = "and"
    OR = "or"
    EQ = "eq"
    LARGER = "larger"
    LESSER = "lesser"
    MOD = "mod"
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    DIV = "div"
    NEG = "neg"

    LPAREN = "("
    RPAREN = ")"
    LBRACE = "{"
    RBRACE = "}"
    COLON = ":"
    SEMICOLON = ";"
    ASSIGN = "="

KEYWORDS: dict[str, TokenType] = {
    "void": TokenType.VOID,
    "num": TokenType.NUM_TYPE,
    "return": TokenType.RETURN,
    "print": TokenType.PRINT,
    "nop": TokenType.NOP,
    "comment": TokenType.COMMENT,
    "if": TokenType.IF,
    "then": TokenType.THEN,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "until": TokenType.UNTIL,
    "do": TokenType.DO,
    "not": TokenType.NOT,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "eq": TokenType.EQ,
    "larger": TokenType.LARGER,
    "lesser": TokenType.LESSER,
    "mod": TokenType.MOD,
    "add": TokenType.ADD,
    "sub": TokenType.SUB,
    "mul": TokenType.MUL,
    "div": TokenType.DIV,
    "neg": TokenType.NEG,
}

PUNCTUATION: dict[str, TokenType] = {
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    ":": TokenType.COLON,
    ";": TokenType.SEMICOLON,
    "=": TokenType.ASSIGN,
}

@dataclass(frozen=True, slots=True)
class Token:
    """One immutable token and the location of its first source character."""

    token_type: TokenType
    lexeme: str
    line: int
    column: int
    offset: int

    def __post_init__(self) -> None:
        if self.line < 1:
            raise ValueError("Token line must be one or greater.")
        if self.column < 1:
            raise ValueError("Token column must be one or greater.")
        if self.offset < 0:
            raise ValueError("Token offset cannot be negative.")
        if self.token_type is TokenType.EOF and self.lexeme:
            raise ValueError("The internal EOF token must have an empty lexeme.")
