"""Deep imported grammar trees and parser-accepted source lower iteratively."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from spl_frontend.codegen import generate_target
from spl_frontend.codegen_ir import UnaryAssign
from spl_frontend.name_analysis import resolve_names
from spl_frontend.target_writer import render_target
from spl_frontend.tree import SyntaxTree
from spl_frontend.tree_reader import read_tree
from spl_frontend.type_analysis import check_types
from spl_frontend.xml_writer import write_tree
from tests.codegen_support import checked_source


CXX = shutil.which('c++') or shutil.which('g++') or shutil.which('clang++')


def _inner(tree, name, parent):
    return tree.add_inner(name, parent.node_id)


def _leaf(tree, value, parent):
    return tree.add_leaf(value, parent.node_id)


def _instruction(tree, algo):
    instruction = _inner(tree, 'INSTR', algo)
    _leaf(tree, ';', algo)
    _inner(tree, 'ALGO', algo)
    return instruction


def _print(tree, algo, text):
    instruction = _instruction(tree, algo)
    _leaf(tree, 'print', instruction)
    output = _inner(tree, 'OUTP', instruction)
    _leaf(tree, '"' + text + '"', output)


def _comparison(tree, boolean):
    _leaf(tree, 'eq', boolean)
    _leaf(tree, '(', boolean)
    for _ in range(2):
        term = _inner(tree, 'TERM', boolean)
        _leaf(tree, '1', term)
    _leaf(tree, ')', boolean)


def _branch(tree, algo):
    instruction = _instruction(tree, algo)
    branch = _inner(tree, 'BRANCH', instruction)
    _leaf(tree, 'if', branch)
    boolean = _inner(tree, 'BOOL', branch)
    _leaf(tree, 'then', branch)
    _leaf(tree, '{', branch)
    yes = _inner(tree, 'ALGO', branch)
    _leaf(tree, '}', branch)
    _leaf(tree, 'else', branch)
    _leaf(tree, '{', branch)
    no = _inner(tree, 'ALGO', branch)
    _leaf(tree, '}', branch)
    return boolean, yes, no


def _deep_tree(kind, depth):
    """Build exact parser productions iteratively, without changing parser."""
    tree = SyntaxTree()
    root = tree.add_root('SPL_PROG')
    program = _inner(tree, 'P', root)
    _inner(tree, 'V_DECL', program)
    _leaf(tree, ':', program)
    _inner(tree, 'F_DECL', program)
    _leaf(tree, ':', program)
    algo = _inner(tree, 'ALGO', program)
    if kind == 'term':
        instruction = _instruction(tree, algo)
        _leaf(tree, 'print', instruction)
        output = _inner(tree, 'OUTP', instruction)
        _leaf(tree, '(', output)
        term = _inner(tree, 'TERM', output)
        _leaf(tree, ')', output)
        for _ in range(depth):
            _leaf(tree, 'neg', term)
            _leaf(tree, '(', term)
            nested = _inner(tree, 'TERM', term)
            _leaf(tree, ')', term)
            term = nested
        _leaf(tree, '1', term)
    elif kind == 'bool':
        boolean, yes, no = _branch(tree, algo)
        _print(tree, yes, 'ok')
        _print(tree, no, 'bad')
        for _ in range(depth):
            _leaf(tree, 'not', boolean)
            _leaf(tree, '(', boolean)
            nested = _inner(tree, 'BOOL', boolean)
            _leaf(tree, ')', boolean)
            boolean = nested
        _comparison(tree, boolean)
    elif kind == 'branch':
        for _ in range(depth):
            boolean, algo, _ = _branch(tree, algo)
            _comparison(tree, boolean)
        _print(tree, algo, 'ok')
    elif kind == 'loop':
        for _ in range(depth):
            instruction = _instruction(tree, algo)
            loop = _inner(tree, 'LOOP', instruction)
            _leaf(tree, 'do', loop)
            _leaf(tree, '{', loop)
            algo = _inner(tree, 'ALGO', loop)
            _leaf(tree, '}', loop)
            condition = _inner(tree, 'COND', loop)
            _leaf(tree, 'until', condition)
            boolean = _inner(tree, 'BOOL', loop)
            _comparison(tree, boolean)
        _print(tree, algo, 'ok')
    else:
        raise ValueError(kind)
    tree.validate()
    return tree


class DeepCodeGenerationTests(unittest.TestCase):
    def _assert_target(self, program, expected):
        target = render_target(program)
        program.validate()
        if CXX is not None:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                source, binary = path / 'deep.cpp', path / 'deep'
                source.write_text(target)
                result = subprocess.run([CXX, '-std=c++17', str(source), '-o', str(binary)],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=3)
                self.assertEqual((run.returncode, run.stdout, run.stderr), (0, expected, ''))

    def test_parser_accepted_600_nested_not_source_avoids_backend_frame_growth(self):
        # The unchanged parser itself is recursive. This depth is accepted by
        # its one-frame BOOL descent but exceeded the former two-frame backend.
        before = sys.getrecursionlimit()
        source = ': : if ' + 'not ( ' * 600 + 'eq ( 1 1 ) ' + ') ' * 600
        source += 'then { print "ok" ; } else { print "bad" ; } ; '
        checked = checked_source(source)
        self._assert_target(generate_target(checked), 'ok')
        self.assertEqual(sys.getrecursionlimit(), before)

    def test_imported_1400_deep_terms_booleans_branches_and_loops(self):
        before = sys.getrecursionlimit()
        for kind in ('term', 'bool', 'branch', 'loop'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                xml = Path(directory) / 'tree.xml'
                # This is the supported flat XML boundary, not an assertion
                # that the original recursive source parser accepts 1400 levels.
                write_tree(_deep_tree(kind, 1400), xml)
                imported = read_tree(xml)
                program = generate_target(check_types(resolve_names(imported, path=xml)))
                if kind == 'term':
                    self.assertEqual(sum(isinstance(i, UnaryAssign) for i in program.fragment.instructions), 1400)
                self._assert_target(program, '1' if kind == 'term' else 'ok')
        self.assertEqual(sys.getrecursionlimit(), before)
