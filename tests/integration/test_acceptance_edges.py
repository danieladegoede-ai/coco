"""High-value SPL boundary cases through the complete front-end pipeline."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from spl_frontend.compiler import compile_file
from spl_frontend.diagnostics import FrontendError


class AcceptanceEdgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.source = self.directory / "SPL.txt"
        self.output = self.directory / "tree.xml"

    def _compile(self, text: str) -> list[str]:
        self.source.write_bytes(text.encode("ascii"))
        compile_file(self.source, self.output)
        document = ET.parse(self.output)
        self.assertEqual(document.getroot().tag, "syntax_tree")
        return [entry.findtext("contents", "") for entry in document.getroot()
                if entry.tag == "leaf"]

    def test_valid_grammar_boundaries_preserve_terminal_lexemes(self) -> None:
        cases = {
            "minimal": ": : ",
            "bare_name": "# : : ",
            "empty_string": ': : comment "" ; ',
            "decimal": ": : print ( -0.001 ) ; ",
            "nested_term": ": : #x = add ( neg ( 1 ) div ( 2 3 ) ) ; ",
            "call_inputs": ": : #f ( 1 #x add ( 2 3 ) ) ; ",
            "empty_branch": ": : if eq ( 1 2 ) then { } else { } ; ",
            "while": ": : while eq ( 1 2 ) do { nop ; } ; ",
            "until": ": : until eq ( 1 2 ) do { } ; ",
            "do_while": ": : do { } while eq ( 1 2 ) ; ",
            "do_until": ": : do { } until eq ( 1 2 ) ; ",
            "void_function": ": void #f ( ) { : : return } : ",
            "num_function": ": num #f ( #x ) { : : return ( #x ) } : ",
        }
        for name, program in cases.items():
            with self.subTest(name=name):
                leaves = self._compile(program)
                self.assertEqual(leaves, program.split())
                self.assertNotIn("$", leaves)

    def test_invalid_boundaries_leave_no_xml_after_a_previous_success(self) -> None:
        cases = {
            "literal_eof_marker": ": : $ ",
            "tab_separator": ":\t: ",
            "negative_zero": ": : print ( -0 ) ; ",
            "leading_zero": ": : print ( 01 ) ; ",
            "fraction_ends_zero": ": : print ( 1.0 ) ; ",
            "uppercase_name": "#A : : ",
            "space_in_string": ': : print "a b" ; ',
            "missing_semicolon": ": : nop ",
            "comma_arguments": ": : #f ( 1 , 2 ) ; ",
            "missing_return": ": void #f ( ) { : : } : ",
            "missing_else": ": : if eq ( 1 2 ) then { } ; ",
            "extra_colon": ": : : ",
            "missing_separator": ": : nop; ",
            "extra_operand": ": : #x = add ( 1 2 3 ) ; ",
            "trailing_token": ": : nop ; nop ",
        }
        for name, program in cases.items():
            with self.subTest(name=name):
                self._compile(": : ")
                self.source.write_bytes(program.encode("ascii"))
                with self.assertRaises(FrontendError):
                    compile_file(self.source, self.output)
                self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
