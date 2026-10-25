"""Tests for the semantic SPL generator."""

import unittest
from pathlib import Path

from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.source import SourceFile
from spl_frontend.tree import SyntaxTree
from spl_frontend.name_analysis import resolve_names, NameAnalysisError
from spl_frontend.type_analysis import check_types, TypeAnalysisError

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
from generate_semantic_spl import (
    generate_semantic_program,
    generate_anchored_programs,
    generate_coverage_program,
    measure_semantic_source,
    SemanticGenerator,
    Scope,
)
import random


def parse_and_check(source: str) -> bool:
    """Parse, resolve names, and type check an SPL source.

    Returns True if all passes succeed, False otherwise.
    """
    try:
        sf = SourceFile(path=Path("test.spl"), text=source)
        tokens = tokenize(sf)
        tree = SyntaxTree()
        parse(tokens, tree, Path("test.spl"))
        tree.validate()
        resolved = resolve_names(tree, path=Path("test.spl"))
        check_types(resolved)
        return True
    except (NameAnalysisError, TypeAnalysisError, ValueError):
        return False


class TestSemanticGeneratorBasic(unittest.TestCase):
    """Test basic semantic generator functionality."""

    def test_generates_non_empty_program(self):
        source, outputs = generate_semantic_program(seed=0)
        self.assertTrue(len(source) > 0)
        self.assertIn(":", source)

    def test_generates_parseable_program(self):
        source, outputs = generate_semantic_program(seed=42)
        sf = SourceFile(path=Path("test.spl"), text=source)
        tokens = tokenize(sf)
        tree = SyntaxTree()
        parse(tokens, tree, Path("test.spl"))
        tree.validate()

    def test_generates_name_valid_program(self):
        source, outputs = generate_semantic_program(seed=123)
        sf = SourceFile(path=Path("test.spl"), text=source)
        tokens = tokenize(sf)
        tree = SyntaxTree()
        parse(tokens, tree, Path("test.spl"))
        tree.validate()
        resolved = resolve_names(tree, path=Path("test.spl"))
        self.assertIsNotNone(resolved)

    def test_generates_type_valid_program(self):
        source, outputs = generate_semantic_program(seed=456)
        self.assertTrue(parse_and_check(source))


class TestSemanticGeneratorDeterminism(unittest.TestCase):
    """Test that generator is deterministic."""

    def test_same_seed_same_output(self):
        source1, out1 = generate_semantic_program(seed=100)
        source2, out2 = generate_semantic_program(seed=100)
        self.assertEqual(source1, source2)
        self.assertEqual(out1, out2)

    def test_different_seeds_different_output(self):
        source1, _ = generate_semantic_program(seed=100)
        source2, _ = generate_semantic_program(seed=200)
        self.assertNotEqual(source1, source2)


class TestSemanticGeneratorNumericModes(unittest.TestCase):
    """Test numeric mode handling."""

    def test_integer_mode_no_div(self):
        source, _ = generate_semantic_program(seed=50, numeric_mode="integer")
        self.assertNotIn("div (", source)

    def test_float_mode_no_mod(self):
        source, _ = generate_semantic_program(seed=50, numeric_mode="float")
        self.assertNotIn("mod (", source)

    def test_integer_mode_valid(self):
        source, _ = generate_semantic_program(seed=789, numeric_mode="integer")
        self.assertTrue(parse_and_check(source))

    def test_float_mode_valid(self):
        source, _ = generate_semantic_program(seed=789, numeric_mode="float")
        self.assertTrue(parse_and_check(source))


class TestSemanticGeneratorSeedRange(unittest.TestCase):
    """Test that a range of seeds all produce valid programs."""

    def test_seed_range_0_to_50(self):
        for seed in range(50):
            with self.subTest(seed=seed):
                source, _ = generate_semantic_program(seed=seed)
                self.assertTrue(
                    parse_and_check(source),
                    f"Seed {seed} produced invalid program: {source[:100]}..."
                )


class TestSemanticGeneratorSizeLimits(unittest.TestCase):
    """Test size limiting."""

    def test_small_max_size(self):
        source, _ = generate_semantic_program(seed=0, max_size=5)
        self.assertLessEqual(measure_semantic_source(source).token_count, 5)

    def test_small_max_depth(self):
        source, _ = generate_semantic_program(seed=0, max_depth=2)
        self.assertTrue(parse_and_check(source))
        self.assertLessEqual(measure_semantic_source(source).expression_depth, 2)


class TestSemanticGeneratorOutputs(unittest.TestCase):
    """Test output tracking."""

    def test_tracks_string_outputs(self):
        gen = SemanticGenerator(
            rng=random.Random(42),
            max_depth=4,
            max_size=30,
        )
        source, outputs = gen.generate()
        from reference_spl_evaluator import evaluate_source
        self.assertEqual(evaluate_source(source), outputs)


class TestAnchoredPrograms(unittest.TestCase):
    """Test the fixed anchored programs."""

    def test_all_anchored_programs_valid(self):
        for name, source, expected in generate_anchored_programs():
            with self.subTest(name=name):
                self.assertTrue(
                    parse_and_check(source),
                    f"Anchored program '{name}' is invalid"
                )

    def test_simple_print_anchor(self):
        programs = generate_anchored_programs()
        simple_print = next(p for p in programs if p[0] == "simple_print")
        name, source, expected = simple_print
        self.assertEqual(expected, ["hello"])

    def test_while_loop_anchor(self):
        programs = generate_anchored_programs()
        while_loop = next(p for p in programs if p[0] == "while_loop")
        name, source, expected = while_loop
        self.assertEqual(expected, ["loop", "loop", "loop"])


class TestScopeTracking(unittest.TestCase):
    """Test the Scope class."""

    def test_scope_variables(self):
        scope = Scope()
        scope.variables.append("#x")
        self.assertEqual(scope.all_variables(), ["#x"])

    def test_scope_initialized(self):
        scope = Scope()
        scope.variables.append("#x")
        scope.initialized.add("#x")
        self.assertEqual(scope.get_initialized_vars(), ["#x"])

    def test_scope_parent_access(self):
        parent = Scope()
        parent.variables.append("#x")
        parent.initialized.add("#x")
        child = Scope(parent=parent)
        child.variables.append("#y")
        self.assertIn("#x", child.all_variables())
        self.assertIn("#y", child.all_variables())

    def test_scope_initialized_from_parent(self):
        parent = Scope()
        parent.variables.append("#x")
        parent.initialized.add("#x")
        child = Scope(parent=parent)
        self.assertEqual(child.get_initialized_vars(), ["#x"])


class TestGeneratorNoLeakedState(unittest.TestCase):
    """Test that generator state doesn't leak between runs."""

    def test_independent_runs(self):
        source1, out1 = generate_semantic_program(seed=1)
        source2, out2 = generate_semantic_program(seed=2)
        source1_again, out1_again = generate_semantic_program(seed=1)
        self.assertEqual(source1, source1_again)
        self.assertEqual(out1, out1_again)


class TestIndependentExpectedEvents(unittest.TestCase):
    def test_all_anchor_expectations_are_hand_computed(self):
        from reference_spl_evaluator import evaluate_source
        for name, source, expected in generate_anchored_programs():
            with self.subTest(name=name):
                self.assertEqual(evaluate_source(source), expected)

    def test_seeded_complete_construct_suite_both_modes(self):
        from reference_spl_evaluator import evaluate_source
        for mode in ("integer", "float"):
            for seed in range(60):
                with self.subTest(mode=mode, seed=seed):
                    source, expected = generate_semantic_program(seed=seed, numeric_mode=mode)
                    self.assertEqual(evaluate_source(source), expected)
                    for construct in ("void", "num", "not", "and", "or", "eq", "lesser", "larger",
                                      "while", "until", "do", "add", "sub", "mul", "neg", "comment", "nop"):
                        self.assertIn(construct, source.split())

    def test_invalid_generation_parameters_reject(self):
        for kwargs in ({"numeric_mode": "bad"}, {"max_size": -1}, {"max_depth": -1}):
            with self.assertRaises(ValueError):
                generate_semantic_program(**kwargs)


class TestEnforcedGenerationBounds(unittest.TestCase):
    def make_generator(self, seed=0, mode="integer", **bounds):
        options = dict(max_depth=4, max_size=1024, max_loops=8,
                       max_iterations=5, max_function_depth=2, max_steps=10000)
        options.update(bounds)
        return SemanticGenerator(random.Random(seed), numeric_mode=mode, **options)

    def observe_execution(self, source, max_steps):
        # Observe real body invocations and shared ticks, without consulting
        # generator counters or its arithmetic/expected-output model.
        from collections import Counter
        from unittest.mock import patch
        from reference_spl_evaluator import Evaluator, Environment
        from spl_frontend.tree_walkers import iter_preorder
        tree = SyntaxTree()
        parse(tokenize(SourceFile(Path("bounded.spl"), source)), tree)
        checked = check_types(resolve_names(tree))
        iterations = Counter()
        ticks = []
        original_tick = Environment.tick

        class ObservedEvaluator(Evaluator):
            def _eval_algo(self, node, env):
                if node.parent_id is not None:
                    parent = self.tree.get_node(node.parent_id)
                    if parent.contents == "LOOP":
                        iterations[parent.node_id] += 1
                return super()._eval_algo(node, env)

        def tick(env):
            ticks.append(None)
            original_tick(env)

        evaluator = ObservedEvaluator(tree, checked.numeric_mode.value.lower())
        with patch.object(Environment, "tick", tick):
            events = evaluator.evaluate(max_steps=max_steps)
        loops = [n.node_id for n in iter_preorder(tree) if n.contents == "LOOP"]
        return events, tuple(iterations[n] for n in loops), len(ticks)

    def check_bounds(self, generator):
        source, expected = generator.generate()
        facts = generator.facts
        self.assertIsNotNone(facts)
        self.assertTrue(parse_and_check(source))
        self.assertEqual(facts.source, measure_semantic_source(source))
        # Independent token and operator nesting checks on these generated
        # sources (their STRINGs contain no whitespace).
        words = source.split()
        self.assertEqual(facts.source.token_count, len(words))
        self.assertLessEqual(len(words), generator.max_size)
        expression_ops = {"add", "sub", "mul", "neg", "mod", "div",
                          "eq", "larger", "lesser", "not", "and", "or"}
        nesting = peak = 0
        stack = []
        for i, word in enumerate(words):
            if word == "(":
                is_op = words[i - 1] in expression_ops or words[i - 1].startswith("#")
                # Exclude function declaration signatures from expressions.
                is_op &= not (i >= 2 and words[i - 2] in ("num", "void"))
                stack.append(is_op)
                nesting += is_op
                peak = max(peak, nesting)
            elif word == ")":
                nesting -= stack.pop()
        self.assertEqual(facts.source.expression_depth, peak)
        self.assertLessEqual(peak, generator.max_depth)
        self.assertLessEqual(facts.source.control_depth, generator.max_depth)
        self.assertLessEqual(facts.source.function_depth, generator.max_function_depth)
        self.assertLessEqual(facts.source.loop_count, generator.max_loops)
        events, iterations, steps = self.observe_execution(source, generator.max_steps)
        self.assertEqual(events, expected)
        self.assertEqual(facts.loop_iterations, iterations)
        self.assertEqual(facts.runtime_steps, steps)
        self.assertTrue(all(n <= generator.max_iterations for n in iterations))
        self.assertLessEqual(steps, generator.max_steps)
        return source, expected, facts

    def test_zero_depth_has_no_operations_calls_or_control(self):
        source, expected, facts = self.check_bounds(self.make_generator(max_depth=0))
        self.assertEqual(facts.source.expression_depth, 0)
        self.assertEqual(facts.source.control_depth, 0)
        self.assertEqual(facts.source.loop_count, 0)
        self.assertEqual(len(expected), 1)

    def test_zero_runtime_budget_returns_empty_program(self):
        source, expected, facts = self.check_bounds(self.make_generator(max_steps=0))
        self.assertEqual((source, expected), (": : ", []))
        self.assertEqual(facts.runtime_steps, 0)

    def test_minimal_and_tight_token_limits(self):
        for size in range(2, 40):
            with self.subTest(size=size):
                source, expected, facts = self.check_bounds(self.make_generator(max_size=size))
                if size < 7:
                    self.assertEqual((source, expected), (": : ", []))
        # No valid SPL source fits zero or one total lexer token.
        for size in (0, 1):
            with self.assertRaisesRegex(ValueError, "at least 2"):
                generate_semantic_program(max_size=size)

    def test_loop_count_one_emits_exactly_one_loop(self):
        _, _, facts = self.check_bounds(self.make_generator(max_loops=1))
        self.assertEqual(facts.source.loop_count, 1)

    def test_zero_loop_and_iteration_budgets(self):
        for bounds in ({"max_loops": 0}, {"max_iterations": 0}):
            with self.subTest(bounds=bounds):
                _, _, facts = self.check_bounds(self.make_generator(**bounds))
                self.assertEqual(facts.source.loop_count, 0)
                self.assertEqual(facts.loop_iterations, ())

    def test_zero_and_one_function_depth(self):
        for depth in (0, 1):
            with self.subTest(depth=depth):
                _, _, facts = self.check_bounds(self.make_generator(max_function_depth=depth))
                self.assertLessEqual(facts.source.function_depth, depth)

    def test_bounds_matrix_is_measured_and_deterministic(self):
        bounds = [
            {"max_depth": n} for n in range(5)
        ] + [
            {"max_loops": n, "max_iterations": 1} for n in range(9)
        ] + [
            {"max_size": 80, "max_function_depth": 0, "max_steps": n}
            for n in (0, 1, 5, 6, 7, 12, 30)
        ]
        for mode in ("integer", "float"):
            for seed in range(3):
                for limits in bounds:
                    with self.subTest(mode=mode, seed=seed, limits=limits):
                        result = self.check_bounds(self.make_generator(seed, mode, **limits))
                        other = self.make_generator(seed, mode, **limits)
                        self.assertEqual(result[:2], other.generate())
                        self.assertEqual(result[2], other.facts)

    def test_facts_measure_handwritten_source(self):
        source = ('#c : num #outer ( ) { : num #child ( ) { : : return ( 1 ) } '
                  ': return ( #child ( ) ) } : #c = 0 ; '
                  'while lesser ( #c 1 ) do { #c = add ( #c 1 ) ; } ; '
                  'print ( sub ( mul ( 4 3 ) neg ( 4 ) ) ) ; ')
        facts = measure_semantic_source(source)
        self.assertEqual(facts.token_count, len(source.split()))
        self.assertEqual((facts.expression_depth, facts.function_depth,
                          facts.control_depth, facts.loop_count), (2, 2, 1, 1))
        self.assertEqual(dict(facts.feature_counts)["call"], 1)

    def test_full_coverage_counts_and_hand_checked_events(self):
        for mode, ratio in (("integer", "1"), ("float", "1.5")):
            # seed 42 selects a=3, b=2, then limit=3. The capture pair
            # prints -1; the child increments q=2 to 3 and captures x=4.
            source, events = generate_coverage_program(42, mode)
            expected = ["-1", "11", "11", "8", "9", ratio,
                        "done", "and", "or", "not", "4"]
            expected += ["0", "1", "2"] * 4 + ["once", "once"]
            self.assertEqual(events, expected)
            facts = measure_semantic_source(source)
            counts = dict(facts.feature_counts)
            self.assertEqual(facts.loop_count, 8)
            self.assertEqual(facts.function_depth, 2)
            for feature in ("add", "sub", "mul", "neg", "eq", "lesser", "larger",
                            "not", "and", "or", "call", "void", "num", "if", "comment", "nop"):
                self.assertGreater(counts[feature], 0)
            for form in ("pre_while", "pre_until", "post_while", "post_until"):
                self.assertEqual(counts[form], 2)
            self.assertEqual(self.observe_execution(source, 10000),
                             (events, (3, 3, 3, 3, 0, 0, 1, 1), 84))

    def test_invalid_new_bounds_reject(self):
        for limits in ({"max_loops": -1}, {"max_iterations": -1},
                       {"max_function_depth": -1}, {"max_steps": -1},
                       {"max_size": 2.5}, {"max_depth": True}):
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                generate_semantic_program(**limits)

    def test_cli_float_flag_is_not_a_positional_seed_or_filename(self):
        import contextlib
        import io
        import os
        import tempfile
        from generate_semantic_spl import main
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmp)
                for args in (["--float"], ["42", "--float"],
                             ["--float", "42", "out.spl"], ["42", "out.spl", "--float"]):
                    with self.subTest(args=args), contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(main(args), 0)
                        path = Path("out.spl" if "out.spl" in args else "semantic_spl.txt")
                        self.assertIn("div (", path.read_text())
                        self.assertFalse(Path("--float").exists())
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
