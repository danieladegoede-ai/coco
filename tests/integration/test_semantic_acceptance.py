"""Integration tests for semantic analysis acceptance.

This test suite runs all semantic test cases from the manifest,
verifying that:
1. Invalid programs fail with the expected error code
2. Valid programs pass all semantic checks
3. All test cases parse successfully before semantic analysis
"""

import json
import unittest
from pathlib import Path

from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.source import SourceFile
from spl_frontend.tree import SyntaxTree
from spl_frontend.name_analysis import resolve_names, NameAnalysisError
from spl_frontend.type_analysis import check_types, TypeAnalysisError
from spl_frontend.numeric_policy import NumericPolicyError


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "semantics"
CASES_FILE = FIXTURES_DIR / "cases.json"


def load_cases() -> list[dict]:
    """Load test cases from manifest."""
    with open(CASES_FILE, "r") as f:
        data = json.load(f)
    return data["cases"]


def parse_source(source: str, path: Path) -> SyntaxTree:
    """Parse source and return syntax tree."""
    sf = SourceFile(path=path, text=source)
    tokens = tokenize(sf)
    tree = SyntaxTree()
    parse(tokens, tree, path)
    tree.validate()
    return tree


def analyze_semantics(tree: SyntaxTree, path: Path) -> tuple[str | None, str | None]:
    """Run semantic analysis and return (phase, error_code) or (None, None) if success."""
    try:
        resolved = resolve_names(tree, path=path)
    except NameAnalysisError as e:
        return ("name_analysis", e.code)

    try:
        check_types(resolved)
    except TypeAnalysisError as e:
        return ("type_analysis", e.code)
    except NumericPolicyError as e:
        return ("type_analysis", e.code)

    return (None, None)


class TestSemanticAcceptance(unittest.TestCase):
    """Test all semantic cases from the manifest."""

    @classmethod
    def setUpClass(cls):
        """Load all test cases."""
        cls.cases = load_cases()

    def test_all_cases_parse(self):
        """Verify all test cases are syntactically valid."""
        for case in self.cases:
            with self.subTest(case_id=case["id"]):
                file_path = FIXTURES_DIR / case["file"]
                source = file_path.read_text()
                try:
                    parse_source(source, file_path)
                except Exception as e:
                    self.fail(f"Case {case['id']} failed to parse: {e}")

    def test_invalid_cases_reject(self):
        """Verify invalid cases are rejected with expected error."""
        for case in self.cases:
            if case["valid"]:
                continue
            with self.subTest(case_id=case["id"]):
                file_path = FIXTURES_DIR / case["file"]
                source = file_path.read_text()
                tree = parse_source(source, file_path)
                phase, code = analyze_semantics(tree, file_path)

                self.assertIsNotNone(
                    code,
                    f"Case {case['id']} should have failed but passed"
                )
                self.assertEqual(
                    code, case["expected_code"],
                    f"Case {case['id']}: expected {case['expected_code']}, got {code}"
                )
                self.assertEqual(
                    phase, case["phase"],
                    f"Case {case['id']}: expected phase {case['phase']}, got {phase}"
                )

    def test_valid_cases_pass(self):
        """Verify valid cases pass semantic analysis."""
        for case in self.cases:
            if not case["valid"]:
                continue
            with self.subTest(case_id=case["id"]):
                file_path = FIXTURES_DIR / case["file"]
                source = file_path.read_text()
                tree = parse_source(source, file_path)
                phase, code = analyze_semantics(tree, file_path)

                self.assertIsNone(
                    code,
                    f"Case {case['id']} should pass but failed with {code} in {phase}"
                )


class TestSpecificAnchorCases(unittest.TestCase):
    """Test specific anchor cases from the spec."""

    def test_mod_div_conflict_exact_message(self):
        """Test that mod+div produces the exact required message."""
        source = "#x : : #x = add ( mod ( 5 2 ) div ( 4 2 ) ) ; "
        tree = parse_source(source, Path("test.spl"))

        with self.assertRaises(TypeAnalysisError) as ctx:
            resolved = resolve_names(tree, path=Path("test.spl"))
            check_types(resolved)

        self.assertEqual(ctx.exception.code, "FLOAT-INT-CONFLICT")
        self.assertEqual(
            ctx.exception.message,
            "A float-integer-conflict might perhaps be possible"
        )

    def test_num_function_as_instruction_rejected(self):
        """Test that num function called as instruction is rejected."""
        source = ": num #f ( ) { : : return ( 1 ) } : #f ( ) ; "
        tree = parse_source(source, Path("test.spl"))
        resolved = resolve_names(tree, path=Path("test.spl"))

        with self.assertRaises(TypeAnalysisError) as ctx:
            check_types(resolved)

        self.assertEqual(ctx.exception.code, "TYPE-INSTR-CALL")

    def test_void_function_in_print_rejected(self):
        """Test that void function used in print is rejected."""
        source = ": void #f ( ) { : : return } : print ( #f ( ) ) ; "
        tree = parse_source(source, Path("test.spl"))
        resolved = resolve_names(tree, path=Path("test.spl"))

        with self.assertRaises(TypeAnalysisError) as ctx:
            check_types(resolved)

        self.assertEqual(ctx.exception.code, "TYPE-TERM-CALL")

    def test_decimal_with_mod_rejected(self):
        """Test that decimal with mod is rejected."""
        source = "#x : : #x = mod ( 5 2.1 ) ; "
        tree = parse_source(source, Path("test.spl"))

        with self.assertRaises(TypeAnalysisError) as ctx:
            resolved = resolve_names(tree, path=Path("test.spl"))
            check_types(resolved)

        self.assertEqual(ctx.exception.code, "DECIMAL-WITH-MOD")


class TestNameAnalysisSpecifics(unittest.TestCase):
    """Test specific name analysis scenarios."""

    def test_undeclared_variable_rejected(self):
        """Test undeclared variable produces correct error."""
        source = ": : #y = 5 ; "
        tree = parse_source(source, Path("test.spl"))

        with self.assertRaises(NameAnalysisError) as ctx:
            resolve_names(tree, path=Path("test.spl"))

        self.assertEqual(ctx.exception.code, "NAME-UNDECLARED-VARIABLE")

    def test_self_call_rejected(self):
        """Test self-recursion produces correct error."""
        source = ": void #f ( ) { : : #f ( ) ; return } : nop ; "
        tree = parse_source(source, Path("test.spl"))

        with self.assertRaises(NameAnalysisError) as ctx:
            resolve_names(tree, path=Path("test.spl"))

        self.assertEqual(ctx.exception.code, "NAME-INVISIBLE-FUNCTION")

    def test_ancestor_access_allowed(self):
        """Test that ancestor variable access is allowed."""
        source = "#x : void #f ( ) { : : #x = 5 ; return } : #f ( ) ; "
        tree = parse_source(source, Path("test.spl"))
        resolved = resolve_names(tree, path=Path("test.spl"))
        self.assertIsNotNone(resolved)


class TestTypeAnalysisSpecifics(unittest.TestCase):
    """Test specific type analysis scenarios."""

    def test_nested_function_types(self):
        """Test that nested functions have correct types."""
        source = "#r : num #outer ( ) { : num #inner ( ) { : : return ( 5 ) } : return ( #inner ( ) ) } : #r = #outer ( ) ; "
        tree = parse_source(source, Path("test.spl"))
        resolved = resolve_names(tree, path=Path("test.spl"))
        checked = check_types(resolved)
        self.assertIsNotNone(checked)

    def test_uncalled_function_still_checked(self):
        """Test that uncalled function bodies are type-checked."""
        source = ": num #f ( ) { : : return ( div ( 5 2 ) ) } : nop ; "
        tree = parse_source(source, Path("test.spl"))
        resolved = resolve_names(tree, path=Path("test.spl"))
        checked = check_types(resolved)
        self.assertIsNotNone(checked)


class TestValidBoundaryCases(unittest.TestCase):
    """Test valid boundary cases that should pass."""

    def test_empty_program_valid(self):
        """Test minimal empty program is valid."""
        source = ": : "
        tree = parse_source(source, Path("test.spl"))
        resolved = resolve_names(tree, path=Path("test.spl"))
        checked = check_types(resolved)
        self.assertIsNotNone(checked)

    def test_all_loop_forms_valid(self):
        """Test all loop forms work."""
        source = "#c : : #c = 0 ; while lesser ( #c 3 ) do { #c = add ( #c 1 ) ; } ; #c = 0 ; until eq ( #c 3 ) do { #c = add ( #c 1 ) ; } ; #c = 0 ; do { #c = add ( #c 1 ) ; } while lesser ( #c 3 ) ; #c = 0 ; do { #c = add ( #c 1 ) ; } until eq ( #c 3 ) ; "
        tree = parse_source(source, Path("test.spl"))
        resolved = resolve_names(tree, path=Path("test.spl"))
        checked = check_types(resolved)
        self.assertIsNotNone(checked)

    def test_all_arithmetic_ops_valid(self):
        """Test all arithmetic operations work."""
        source = "#x : : #x = add ( 1 2 ) ; #x = sub ( 3 1 ) ; #x = mul ( 2 3 ) ; #x = neg ( 5 ) ; "
        tree = parse_source(source, Path("test.spl"))
        resolved = resolve_names(tree, path=Path("test.spl"))
        checked = check_types(resolved)
        self.assertIsNotNone(checked)

    def test_all_boolean_ops_valid(self):
        """Test all boolean operations work."""
        source = ": : if eq ( 1 1 ) then { nop ; } else { nop ; } ; if larger ( 2 1 ) then { nop ; } else { nop ; } ; if lesser ( 1 2 ) then { nop ; } else { nop ; } ; if not ( eq ( 1 2 ) ) then { nop ; } else { nop ; } ; if and ( eq ( 1 1 ) eq ( 2 2 ) ) then { nop ; } else { nop ; } ; if or ( eq ( 1 2 ) eq ( 1 1 ) ) then { nop ; } else { nop ; } ; "
        tree = parse_source(source, Path("test.spl"))
        resolved = resolve_names(tree, path=Path("test.spl"))
        checked = check_types(resolved)
        self.assertIsNotNone(checked)


if __name__ == "__main__":
    unittest.main()
