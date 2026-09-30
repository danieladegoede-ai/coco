"""Broad black-box style SPL corpus with an explicit oracle for each input.

The corpus exercises the real source reader, lexer, parser, tree validator and
XML writer. Cases are distinct source files, not repeated assertions on one
program. Structural corruption and filesystem fault injection remain in their
focused unit and integration modules.
"""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from spl_frontend.compiler import compile_file
from spl_frontend.diagnostics import FrontendError


@dataclass(frozen=True)
class Edge:
    name: str
    source: bytes
    accepts: bool


def _ascii(text: str) -> bytes:
    return text.encode("ascii")


def edge_corpus() -> list[Edge]:
    """Build distinct documented inputs spanning lexical and grammar edges."""
    cases: list[Edge] = []
    seen: dict[bytes, bool] = {}

    def add(name: str, program: str | bytes, accepts: bool) -> None:
        source = _ascii(program) if isinstance(program, str) else program
        if source in seen:
            if seen[source] != accepts:
                raise AssertionError(f"Conflicting edge-case oracles for {source!r}")
            return
        seen[source] = accepts
        cases.append(Edge(name, source, accepts))

    valid_numbers = (
        "0", "1", "9", "10", "99", "123456789", "-1", "-9", "-10", "-99",
        "0.1", "0.01", "0.001", "0.9", "-0.1", "-0.01", "-1.1", "-12.34",
        "1.01", "1.001", "123.456", "999999.9991", "0.00001", "10.0001",
        "-123456789.1",
    )
    invalid_numbers = (
        "-0", "00", "01", "-01", "1.0", "0.0", "-0.0", "1.230", "1.",
        "-1.", ".1", "-.1", "+1", "1e3", "1..2", "--1", "1-2", "0.00",
        "00.1", "-00.1", "10.00", "0123", "-", "1a", "0x1",
    )
    for value in valid_numbers:
        add(f"valid number {value}", f": : print ( {value} ) ; ", True)
    for value in invalid_numbers:
        add(f"invalid number {value}", f": : print ( {value} ) ; ", False)

    valid_names = (
        "#", "#a", "#z", "#0", "#9", "#a0", "#0a", "#abc", "#abc123",
        "#123abc", "#x1", "#zz", "#000", "#a9z", "#q", "#m42", "#s0",
        "#p99", "#a123456789", "#abcdefghijklmnop", "#z987654321", "#1x",
        "#v0v0", "#n123n", "#xxxxxxxxxxxxxxxxxxxxxxxx",
    )
    invalid_names = (
        "#A", "#aA", "#_", "#-", "#a.b", "#a#b", "a", "A", "PRINT",
        "Print", "print1", "void1", "#x_y", "#x/y", "#x'", "#x@", "#x!",
        "#x?", "#x,", "#x:", "#x;", "#x)", "#x(", "#x=", "#é",
    )
    for value in valid_names:
        add(f"valid name {value}", f"{value} : : ", True)
    for value in invalid_names:
        add(f"invalid name {value}", f"{value} : : ".encode("utf-8"), False)

    valid_strings = (
        "", "a", "abc123", "0", "9", "hello,world.", ",.:-?!", "a,b",
        "a.b", "a:b", "a-b", "a?b", "a!b", "1234567890", "zzzz", "ok",
        "hello", "note", "x", "value", "a0z9", "0.1", "-1", "?!",
        "abcdefghijklmnopqrstuvwxyz",
    )
    invalid_strings = (
        "A", "a b", "a\tb", "a\nb", "a\rb", "a_b", "a#b", "a;b",
        "a(b", "a{b", "a/b", "a\\b", "a'b", "a&b", "a<b", "a>b",
        "a@b", "a$b", "a+b", "a=b", "a\x00b", "é", "a\"b", "a[b",
        "a]b",
    )
    for value in valid_strings:
        add(f"valid string {value!r}", f': : comment "{value}" ; ', True)
    for value in invalid_strings:
        add(f"invalid string {value!r}",
            f': : comment "{value}" ; '.encode("utf-8"), False)

    valid_grammar = (
        ": : ", "# : : ", "#x #y : : ", ": : nop ; ",
        ': : print "ok" ; ', ': : print ( 0 ) ; ',
        ': : comment "" ; ', ": : #x = 0 ; ", ": : #f ( ) ; ",
        ": : #f ( 1 ) ; ", ": : #f ( 1 #x ) ; ",
        ": : #x = #y ; ", ": : #x = #f ( ) ; ",
        ": : #x = mod ( 1 2 ) ; ", ": : #x = add ( 1 2 ) ; ",
        ": : #x = sub ( 1 2 ) ; ", ": : #x = mul ( 1 2 ) ; ",
        ": : #x = div ( 1 2 ) ; ", ": : #x = neg ( 1 ) ; ",
        ": : if eq ( 1 2 ) then { } else { } ; ",
        ": : if larger ( 2 1 ) then { nop ; } else { } ; ",
        ": : if lesser ( 1 2 ) then { } else { nop ; } ; ",
        ": : if not ( eq ( 1 2 ) ) then { } else { } ; ",
        ": : if and ( eq ( 1 2 ) eq ( 3 4 ) ) then { } else { } ; ",
        ": : if or ( eq ( 1 2 ) eq ( 3 4 ) ) then { } else { } ; ",
        ": : while eq ( 1 2 ) do { } ; ",
        ": : until eq ( 1 2 ) do { } ; ",
        ": : do { } while eq ( 1 2 ) ; ",
        ": : do { } until eq ( 1 2 ) ; ",
        ": void #f ( ) { : : return } : ",
        ": num #f ( ) { : : return ( 1 ) } : ",
        ": void #f ( #x ) { : : return } : ",
        ": num #f ( #x #y ) { : : return ( #x ) } : ",
        ": void #f ( ) { : void #g ( ) { : : return } : return } : ",
        ": : #x = add ( neg ( 1 ) mul ( 2 3 ) ) ; ",
    )
    for index, program in enumerate(valid_grammar, 1):
        add(f"valid grammar production {index}", program, True)

    invalid_grammar = (
        "", " ", ": ", ": : : ", ": : ; ", ": : nop ",
        ': : print "ok" ', ": : print ( 1 ; ", ": : print ( ) ; ",
        ': : comment ; ', ": : #x ; ", ": : #x = ; ",
        ": : #f ( 1 , 2 ) ; ", ": : #f ( 1 ; ",
        ": : #x = add ( 1 ) ; ", ": : #x = add ( 1 2 3 ) ; ",
        ": : #x = neg ( 1 2 ) ; ", ": : #x = mod ( ) ; ",
        ": : if eq ( 1 2 ) { } else { } ; ",
        ": : if eq ( 1 2 ) then { } ; ",
        ": : if eq ( 1 2 ) then { } else } ; ",
        ": : while eq ( 1 2 ) { } ; ",
        ": : do { } eq ( 1 2 ) ; ",
        ": : do { } while ; ",
        ": void #f ( ) { : : } : ",
        ": void #f ( ) { : : return ( 1 ) } : ",
        ": num #f ( ) { : : return } : ",
        ": num #f ( ) { : : return ( ) } : ",
        ": void ( ) { : : return } : ",
        ": void #f ( { : : return } : ",
        ": void #f ( ) : : return } : ",
        ": : return ", ": : nop ; : ",
        ": : nop ; nop ", ": : $ ",
    )
    for index, program in enumerate(invalid_grammar, 1):
        add(f"invalid grammar production {index}", program, False)

    add("missing final blank_space", ": :", False)

    separators = (" ", "  ", "\n", "\r", "\r\n")
    for first in separators:
        for second in separators:
            add(f"separator {first!r} then {second!r}",
                f"{first}:{second}:{first}", True)

    joined_templates = (
        ": : print ( add ( 1 2 ) ) ; ",
        ": : #x = mul ( 3 4 ) ; ",
        ": : if eq ( 1 2 ) then { } else { } ; ",
    )
    for template_index, program in enumerate(joined_templates, 1):
        tokens = program.split()
        for position in range(len(tokens) - 1):
            joined = tokens[:position] + [tokens[position] + tokens[position + 1]]
            joined += tokens[position + 2:]
            add(f"missing separator {template_index}/{position}",
                " ".join(joined) + " ", False)

    trailing_tokens = (
        "nop", "print", "comment", "if", "then", "else", "while", "until",
        "do", "return", "void", "num", "add", "sub", "mul", "div", "neg",
        "eq", "larger", "lesser", "#x", "0", "$", "@", ";",
    )
    for value in trailing_tokens:
        add(f"trailing token {value}", f": : {value} ", False)

    instruction_pairs = (
        "nop", 'comment "a"', 'print "a"', "print ( 0 )",
        "#x = 1", "#f ( )", "if eq ( 1 2 ) then { } else { }",
        "while eq ( 1 2 ) do { }", "do { } until eq ( 1 2 )",
        "#x = add ( 1 2 )",
    )
    for first_index, first in enumerate(instruction_pairs, 1):
        for second_index, second in enumerate(instruction_pairs[:5], 1):
            add(f"instruction pair {first_index}/{second_index}",
                f": : {first} ; {second} ; ", True)

    return cases


class FullPipelineEdgeCorpusTests(unittest.TestCase):
    def test_distinct_edge_inputs_have_correct_outcome_and_output(self) -> None:
        cases = edge_corpus()
        self.assertGreaterEqual(len(cases), 300)
        self.assertEqual(len(cases), len({case.name for case in cases}))
        self.assertEqual(len(cases), len({case.source for case in cases}))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "SPL.txt"
            output = Path(directory) / "tree.xml"
            for case in cases:
                with self.subTest(case=case.name):
                    source.write_bytes(case.source)
                    if case.accepts:
                        compile_file(source, output)
                        document = ET.parse(output).getroot()
                        self.assertEqual(document.tag, "syntax_tree")
                        leaves = [entry.findtext("contents") for entry in document
                                  if entry.tag == "leaf"]
                        self.assertEqual(leaves, case.source.decode("ascii").split())
                        self.assertNotIn("$", leaves)
                    else:
                        output.write_bytes(b"old result")
                        with self.assertRaises(FrontendError):
                            compile_file(source, output)
                        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
