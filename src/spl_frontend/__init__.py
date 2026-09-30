"""Shared foundation for the COS341 SPL front end."""

__version__ = "0.1.0"

from .diagnostics import FrontendError
from .tokens import Token, TokenType
from .lexer import tokenize
from .token_stream import TokenStream
from .source import SourceFile, load_source

__all__ = [
    "Token",
    "TokenType",
    "tokenize",
    "FrontendError",
    "TokenStream",
    "SourceFile",
    "load_source",
]