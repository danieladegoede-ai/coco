"""Full CLI/XML/semantic/target execution assertions for the SYS0001-0500 cases."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from spl_frontend.compiler import compile_tree
from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.source import SourceFile
from spl_frontend.tree import SyntaxTree
from spl_frontend.tree_reader import read_tree
from tests.system500_cases import SystemCase
from tools.target_inspector import inspect_target

ROOT = Path(__file__).resolve().parents[1]
CXX = shutil.which('c++') or shutil.which('g++') or shutil.which('clang++')
# A fresh interpreter enters the public module, with absolute import paths even
# when the caller supplied a relative PYTHONPATH. Never changes the parent cwd.
CLI = [sys.executable, '-c',
       f'import runpy,sys;sys.path.insert(0,{str(ROOT / "src")!r});'
       'runpy.run_module("spl_frontend",run_name="__main__")']


def exercise(test: unittest.TestCase, case: SystemCase) -> None:
    logs: list[dict] = []
    with tempfile.TemporaryDirectory(prefix='spl system500 ') as temporary:
        work = Path(temporary)
        source = work / 'SPL.txt'
        xml = work / 'tree.xml'
        target = work / 'program.cpp'

        def process(argv: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
            try:
                result = subprocess.run(argv, cwd=work, text=True, capture_output=True,
                                        encoding='utf-8', timeout=timeout, check=False)
            except subprocess.TimeoutExpired as exc:
                def decoded(value: str | bytes | None) -> str:
                    return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else (value or '')
                logs.append({'argv':argv, 'status':'timeout', 'timeout_seconds':timeout,
                             'stdout':decoded(exc.stdout), 'stderr':decoded(exc.stderr)})
                raise
            except OSError as exc:
                logs.append({'argv':argv, 'status':'unavailable', 'stdout':'', 'stderr':str(exc)})
                raise
            logs.append({'argv':argv, 'status':result.returncode,
                         'stdout':result.stdout,'stderr':result.stderr})
            return result

        def cli(path: Path | None = None) -> subprocess.CompletedProcess[str]:
            return process(CLI + ([str(path)] if path is not None else []))

        def successful(result: subprocess.CompletedProcess[str]) -> None:
            test.assertEqual(result.returncode, 0, result.stderr)
            test.assertEqual(result.stdout, '')
            test.assertEqual(result.stderr, '')
            test.assertTrue(xml.is_file(), 'Full CLI must publish tree.xml')
            test.assertTrue(target.is_file(), 'Full CLI must publish program.cpp')
            read_tree(xml).validate()

        def execute_target(expected: str) -> None:
            generated = target.read_text(encoding='utf-8')
            test.assertEqual(inspect_target(generated), ())
            test.assertIsNotNone(CXX, 'A C++ compiler is required; this suite must not skip execution')
            executable = work / ('program.exe' if os.name=='nt' else 'program')
            compiled = process([str(CXX), '-std=c++17', '-Wall', '-Wextra', '-pedantic',
                                str(target), '-o', str(executable)])
            test.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = process([str(executable)], timeout=5)
            test.assertEqual(executed.returncode, 0, executed.stderr)
            test.assertEqual(executed.stderr, '')
            test.assertEqual(executed.stdout, expected)

        def rejected(result: subprocess.CompletedProcess[str]) -> None:
            test.assertEqual(result.returncode, case.status, result.stderr)
            test.assertEqual(result.stdout, '')
            test.assertIn(case.code, result.stderr)
            test.assertIn(source.name, result.stderr)
            location = re.search(re.escape(str(source)) + r':(\d+):(\d+):', result.stderr)
            test.assertIsNotNone(location, 'Diagnostic must identify the actual input path and position')
            line, column = map(int, location.groups())
            # These rejection fixtures put the fault on their only nonempty
            # line; leading newlines deliberately exercise source offsets.
            expected_line = len(case.source) - len(case.source.lstrip('\n')) + 1
            test.assertEqual(line, expected_line, 'Diagnostic lost the leading-line offset')
            test.assertGreaterEqual(column, 1)
            test.assertLessEqual(column, len(case.source.split('\n')[line-1]) + 1)
            if case.code == 'FLOAT-INT-CONFLICT':
                test.assertIn('A float-integer-conflict might perhaps be possible', result.stderr)
            test.assertNotIn('Traceback', result.stderr)
            test.assertFalse(xml.exists(), 'No stale/partial XML after failed full compilation')
            test.assertFalse(target.exists(), 'No stale/partial target after failed full compilation')

        try:
            source.write_bytes(case.source.encode('utf-8'))
            if case.family == 'deep':
                limit = sys.getrecursionlimit()
                parse(tokenize(SourceFile(source, case.source)), SyntaxTree(), source)
                test.assertEqual(sys.getrecursionlimit(), limit, 'Parser must not change process recursion policy')
            if case.profile in ('reject', 'recovery'):
                # Name/type/generation negatives are independently grammar-valid.
                if case.status >= 7:
                    parse(tokenize(SourceFile(source, case.source)), SyntaxTree(), source)
                if case.profile == 'recovery':
                    source.write_text(f': : print ( {case.stdout} ) ; ', encoding='utf-8')
                    successful(cli())
                    source.write_bytes(case.source.encode('utf-8'))
                else:
                    xml.write_text('stale XML', encoding='utf-8')
                    target.write_text('stale target', encoding='utf-8')
                rejected(cli(source))
                test.assertEqual(source.read_bytes(), case.source.encode())
                if case.profile == 'recovery':
                    source.write_text(f': : print ( {case.stdout} ) ; ', encoding='utf-8')
                    successful(cli())
                    execute_target(case.stdout)
            else:
                successful(cli())
                test.assertEqual(source.read_bytes(), case.source.encode())
                execute_target(case.stdout)
                if case.profile == 'xml-roundtrip':
                    tree = read_tree(xml)
                    original = [(n.node_id,n.contents,n.parent_id,tuple(n.child_ids)) for n in tree.iter_nodes()]
                    result = compile_tree(tree, path=xml)
                    test.assertEqual(result.target_source, target.read_text(encoding='utf-8'))
                    test.assertEqual(original, [(n.node_id,n.contents,n.parent_id,tuple(n.child_ids)) for n in tree.iter_nodes()])
                elif case.profile.startswith(('xml-', 'target-')):
                    alias = xml if case.profile.startswith('xml-') else target
                    if case.profile.endswith('hardlink'):
                        alias.unlink()
                        os.link(source, alias)
                        input_path = source
                    else:
                        alias.write_bytes(case.source.encode())
                        input_path = alias
                    if case.profile.endswith('relative'):
                        (work / 'subdir').mkdir()
                        input_path = Path('subdir') / '..' / alias.name
                    snapshot = {p:p.read_bytes() for p in (source,xml,target)}
                    result = cli(input_path)
                    test.assertEqual(result.returncode, 3, result.stderr)
                    test.assertIn('IO-INPUT-OUTPUT-SAME', result.stderr)
                    test.assertEqual(snapshot, {p:p.read_bytes() for p in snapshot})
        except Exception:
            destination = ROOT / 'build' / 'system500-failures' / case.case_id
            shutil.copytree(work, destination, dirs_exist_ok=True)
            (destination / 'expected.json').write_text(json.dumps(case.inventory(),indent=2)+'\n')
            (destination / 'stages.json').write_text(json.dumps(logs,indent=2)+'\n')
            (destination / 'reproduce.txt').write_text(
                f'From the repository root:\nPYTHONPATH=src python3 -m unittest '
                f'tests.integration.test_system_500.CompleteSystem500Tests.test_{case.case_id}_{case.family} -v\n')
            raise
