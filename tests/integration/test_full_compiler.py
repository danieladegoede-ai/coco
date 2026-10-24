"""Full default command, semantic phases, XML equivalence and output safety."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spl_frontend.cli import main
from spl_frontend.compiler import compile_program, compile_tree
from spl_frontend.diagnostics import FrontendError
from spl_frontend.tree_reader import read_tree
from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.source import SourceFile
from spl_frontend.tree import SyntaxTree
from spl_frontend.type_analysis import TypeAnalysisError
from spl_frontend.codegen_ir import CodegenError
from tests.codegen_support import TARGET_CXX, compile_and_run_target


class FullCompilerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.old_cwd = Path.cwd()
        os.chdir(self.directory)
        self.addCleanup(os.chdir, self.old_cwd)
        self.source = self.directory / 'SPL.txt'
        self.target = self.directory / 'program.cpp'
        self.xml = self.directory / 'tree.xml'

    def run_cli(self, source, args=None):
        self.source.write_text(source, encoding='ascii')
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = main([] if args is None else args)
        self.assertEqual(out.getvalue(), '')
        self.assertNotIn('Traceback', err.getvalue())
        return status, err.getvalue()

    def test_default_reaches_full_generation_and_keeps_original_xml(self):
        status, error = self.run_cli('#x : : #x = div ( 5 2 ) ; print ( #x ) ; ')
        self.assertEqual(status, 0, error)
        self.assertTrue(self.target.is_file())
        self.assertIn('int main', self.target.read_text())
        self.assertTrue(self.xml.is_file())
        tree = read_tree(self.xml)
        self.assertTrue(any(n.contents == '#x' for n in tree.iter_nodes()))

    def test_semantic_phases_and_valid_error_valid_lifecycle(self):
        cases = [
            (': : print "ok" ; ', 0, ''),
            (': : @ ', 4, 'lexer['),
            (': ', 5, 'syntax['),
            (': : #missing = 1 ; ', 7, 'name['),
            (': void #f ( ) { : : return } : print ( #f ( ) ) ; ', 8, 'type['),
            ('#x : : #x = add ( mod ( 5 2 ) div ( 4 2 ) ) ; ', 8,
             'A float-integer-conflict might perhaps be possible'),
            (': void #f ( #a ) { : : return } : #f ( ) ; ', 9, 'codegen['),
        ]
        for source, expected, fragment in cases:
            with self.subTest(source=source):
                self.target.write_text('stale target')
                self.xml.write_text('stale XML')
                status, error = self.run_cli(source)
                self.assertEqual(status, expected, error)
                self.assertIn(fragment, error)
                self.assertEqual(self.target.exists(), expected == 0)
                self.assertEqual(self.xml.exists(), expected == 0)
                status, error = self.run_cli(': : print "fresh" ; ')
                self.assertEqual(status, 0, error)
                self.assertIn('fresh', self.target.read_text())

    def test_explicit_path_with_spaces_and_source_diagnostics(self):
        custom = self.directory / 'input with spaces.spl'
        custom.write_text(': : print "ok" ; ')
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = main([str(custom)])
        self.assertEqual(status, 0, err.getvalue())
        custom.write_text(': :\nprint ( #missing ) ;\n')
        with redirect_stderr(err):
            status = main([str(custom)])
        self.assertEqual(status, 7)
        self.assertIn(f'{custom}:2:9', err.getvalue())
        self.assertFalse(self.target.exists())

    def test_frontend_mode_preserves_syntax_only_cases(self):
        source = ': : #undeclared = 1 ; '
        status, error = self.run_cli(source, ['--frontend'])
        self.assertEqual(status, 0, error)
        self.assertTrue(self.xml.exists())
        self.assertFalse(self.target.exists())
        status, _ = self.run_cli(source)
        self.assertEqual(status, 7)
        self.assertFalse(self.xml.exists())

    def test_input_equal_either_output_is_protected_before_any_deletion(self):
        for source in (self.target, self.xml):
            with self.subTest(source=source):
                source.write_text(': : ')
                before = source.read_bytes()
                with self.assertRaises(FrontendError) as raised:
                    compile_program(source, self.target, xml_path=self.xml)
                self.assertEqual(raised.exception.diagnostic.code, 'IO-INPUT-OUTPUT-SAME')
                self.assertEqual(source.read_bytes(), before)

    def test_hardlink_input_alias_is_protected(self):
        self.source.write_text(': : ')
        os.link(self.source, self.target)
        with self.assertRaises(FrontendError) as raised:
            compile_program(self.source, self.target, xml_path=self.xml)
        self.assertEqual(raised.exception.diagnostic.code, 'IO-INPUT-OUTPUT-SAME')
        self.assertEqual(self.source.read_text(), ': : ')
        self.assertEqual(self.target.read_text(), ': : ')

    def test_output_alias_is_rejected_without_deleting_source_or_output(self):
        self.source.write_text(': : ')
        self.target.write_text('keep')
        with self.assertRaises(FrontendError) as raised:
            compile_program(self.source, self.target, xml_path=self.target)
        self.assertEqual(raised.exception.diagnostic.code, 'IO-OUTPUT-ALIAS')
        self.assertEqual(self.target.read_text(), 'keep')

    def test_missing_input_invalidates_both_old_outputs(self):
        self.target.write_text('stale')
        self.xml.write_text('stale')
        with self.assertRaises(FrontendError):
            compile_program(self.source, self.target, xml_path=self.xml)
        self.assertFalse(self.target.exists())
        self.assertFalse(self.xml.exists())

    def test_target_publication_failure_rolls_back_xml_and_cleans_temporary(self):
        self.source.write_text(': : ')
        original = tempfile.NamedTemporaryFile
        def deny_target(*args, **kwargs):
            if kwargs.get('mode') == 'w':
                raise OSError('denied')
            return original(*args, **kwargs)
        with patch('spl_frontend.compiler.tempfile.NamedTemporaryFile', side_effect=deny_target):
            with self.assertRaises(FrontendError) as raised:
                compile_program(self.source, self.target, xml_path=self.xml)
        self.assertEqual(int(raised.exception.exit_code), 9)
        self.assertFalse(self.xml.exists())
        self.assertFalse(self.target.exists())
        self.assertFalse(list(self.directory.glob('.*.tmp')))

    def test_xml_publication_failure_does_not_publish_target(self):
        self.source.write_text(': : ')
        with patch('spl_frontend.compiler.write_tree', side_effect=OSError('denied')):
            with self.assertRaises(OSError):
                compile_program(self.source, self.target, xml_path=self.xml)
        self.assertFalse(self.target.exists())
        self.assertFalse(self.xml.exists())

    def test_xml_semantic_generation_matches_source_pipeline(self):
        self.source.write_text(
            '#x : num #f ( #a ) { : : return ( add ( #a 1 ) ) } '
            ': #x = #f ( 4 ) ; print ( #x ) ; '
        )
        result = compile_program(self.source, self.target, xml_path=self.xml)
        imported = compile_tree(read_tree(self.xml), path=self.xml)
        self.assertEqual(result.target_source, imported.target_source)
        self.assertEqual(result.checked.resolved.binding_by_name_node,
                         imported.checked.resolved.binding_by_name_node)

    def test_xml_only_type_error_retains_file_and_node_without_fake_lines(self):
        path = self.directory/'imported with spaces.xml'
        text = ': void #f ( ) { : : return } : print ( #f ( ) ) ; '
        tree = parse(tokenize(SourceFile(Path('original.spl'), text)), SyntaxTree())
        with self.assertRaises(TypeAnalysisError) as raised:
            compile_tree(tree, path=path)
        self.assertIn(f'{path}:node[', raised.exception.render())
        self.assertIsNone(raised.exception.span)

    @unittest.skipUnless(TARGET_CXX, "C++ compiler required for full CLI execution")
    def test_public_command_reaches_executable_arithmetic_and_nested_repeated_calls(self):
        examples = [
            ('#x : : #x = div ( 5 2 ) ; print ( #x ) ; ', '2.5'),
            ('#x : num #f ( #a ) { #local : void #g ( ) { : : '
             '#local = add ( #local 1 ) ; return } : #local = #a ; #g ( ) ; '
             'return ( #local ) } : #x = #f ( 4 ) ; print ( #x ) ; print ":" ; '
             '#x = #f ( 8 ) ; print ( #x ) ; ', '5:9'),
        ]
        source_root = Path(__file__).resolve().parents[2] / 'src'
        for source, expected in examples:
            with self.subTest(expected=expected):
                self.source.write_text(source, encoding='ascii')
                cli = subprocess.run([sys.executable, '-m', 'spl_frontend'],
                                     cwd=self.directory, env={**os.environ, 'PYTHONPATH': str(source_root)},
                                     capture_output=True, text=True, timeout=10)
                self.assertEqual((cli.returncode, cli.stdout, cli.stderr), (0, '', ''))
                _, run = compile_and_run_target(self.target.read_text())
                self.assertEqual((run.returncode, run.stdout, run.stderr), (0, expected, ''))

    def test_xml_only_generation_error_retains_file_and_node_without_fake_lines(self):
        path = self.directory / 'imported with spaces.xml'
        text = ': void #f ( #a ) { : : return } : #f ( ) ; '
        tree = parse(tokenize(SourceFile(Path('original.spl'), text)), SyntaxTree())
        with self.assertRaises(CodegenError) as caught:
            compile_tree(tree, path=path)
        self.assertIn(f'{path}:node[', caught.exception.render())
        self.assertIsNone(caught.exception.span)

    def test_hardlinked_output_aliases_are_rejected_before_cleanup(self):
        self.source.write_text(': : ')
        self.target.write_text('keep both links')
        os.link(self.target, self.xml)
        with self.assertRaises(FrontendError) as caught:
            compile_program(self.source, self.target, xml_path=self.xml)
        self.assertEqual(caught.exception.diagnostic.code, 'IO-OUTPUT-ALIAS')
        self.assertEqual(self.target.read_text(), 'keep both links')
        self.assertEqual(self.xml.read_text(), 'keep both links')
        self.assertEqual(self.source.read_text(), ': : ')

    def test_unreadable_input_clears_stale_outputs_and_reports_status_three(self):
        self.target.write_text('stale target')
        self.xml.write_text('stale XML')
        with patch('spl_frontend.compiler.load_source', side_effect=PermissionError('denied')):
            status, error = self.run_cli(': : ', [str(self.source)])
        self.assertEqual(status, 3, error)
        self.assertIn('IO-INPUT-READ', error)
        self.assertIn(str(self.source), error)
        self.assertFalse(self.target.exists())
        self.assertFalse(self.xml.exists())

    def test_target_replace_failure_rolls_back_published_xml_and_temporary(self):
        original = os.replace
        def deny_target(source, destination):
            if Path(destination) == self.target:
                raise PermissionError('target replace denied')
            return original(source, destination)
        self.source.write_text(': : ')
        with patch('spl_frontend.compiler.os.replace', side_effect=deny_target):
            with self.assertRaises(FrontendError) as caught:
                compile_program(self.source, self.target, xml_path=self.xml)
        self.assertEqual(int(caught.exception.exit_code), 9)
        self.assertFalse(self.target.exists())
        self.assertFalse(self.xml.exists())
        self.assertFalse(list(self.directory.glob('.*.tmp')))

    def test_all_mutation_families_reject_through_cli_without_stale_outputs(self):
        from tools.generate_semantic_spl import generate_coverage_program
        from tools.mutate_semantic_spl import generate_mutation, MutationType
        for seed in (0, 341):
            source, _ = generate_coverage_program(seed)
            for kind in MutationType.__args__:
                with self.subTest(seed=seed, kind=kind):
                    self.assertEqual(self.run_cli(source)[0], 0)
                    mutation = generate_mutation(source, kind, seed)
                    self.assertIsNotNone(mutation)
                    status, error = self.run_cli(mutation.mutated_source)
                    self.assertIn(status, (7, 8), error)
                    self.assertIn(mutation.expected_code, error)
                    self.assertFalse(self.target.exists())
                    self.assertFalse(self.xml.exists())
                    self.assertEqual(self.run_cli(source)[0], 0)

    def test_all_semantic_manifest_cases_through_final_cli(self):
        fixture_root = Path(__file__).resolve().parents[1] / 'fixtures' / 'semantics'
        cases = json.loads((fixture_root / 'cases.json').read_text())['cases']
        for case in cases:
            with self.subTest(case=case['id']):
                status, error = self.run_cli((fixture_root / case['file']).read_text())
                self.assertEqual(status == 0, case['valid'], error)
                if not case['valid']:
                    self.assertIn(case['expected_code'], error)
                    self.assertFalse(self.target.exists())
                    self.assertFalse(self.xml.exists())


if __name__ == '__main__':
    unittest.main()
