"""Exercise real CLI, original XML, public APIs and actual native targets."""
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
from spl_frontend.tree_reader import read_tree, parse_tree_xml
from spl_frontend.tree_walkers import iter_leaves
from spl_frontend.semantic_model import FoundationError
from tests.edge5000.cases import EdgeCase,position
from tools.target_inspector import inspect_target

ROOT=Path(__file__).resolve().parents[2]
CXX=shutil.which('c++') or shutil.which('g++') or shutil.which('clang++')
CLI=[sys.executable,'-c',f'import runpy,sys;sys.path.insert(0,{str(ROOT/"src")!r});runpy.run_module("spl_frontend",run_name="__main__")']


def _record(tree) -> list:
    return sorted((n.node_id,n.contents,n.parent_id,tuple(n.child_ids)) for n in tree.iter_nodes())


def _checked(source: str, path: Path):
    tokens=tokenize(SourceFile(path,source))
    tree=parse(tokens,SyntaxTree(),path)
    return tree,compile_tree(tree,path=path)


def exercise(test: unittest.TestCase, case: EdgeCase, *, compiler_command: list[str] | None = None) -> None:
    compiler = list(compiler_command) if compiler_command is not None else CLI
    evidence={'compiler_runs':0,'native_compiles':0,'native_runs':0,'partner_checks':0,'api_checks':0}
    test.edge_evidence=evidence
    logs=[]
    with tempfile.TemporaryDirectory(prefix='spl edge 5000 ') as directory:
        work=Path(directory);source=work/'SPL.txt';xml=work/'tree.xml';target=work/'program.cpp'
        def process(stage: str, argv: list[str],timeout: int=30):
            try:
                result=subprocess.run(argv,cwd=work,capture_output=True,text=True,encoding='utf-8',
                                      env={**os.environ,'PYTHONIOENCODING':'utf-8'},timeout=timeout,check=False)
            except (subprocess.TimeoutExpired,OSError) as exc:
                def text(value):return value.decode('utf-8',errors='replace') if isinstance(value,bytes) else value or ''
                logs.append({'stage':stage,'argv':argv,'status':'timeout' if isinstance(exc,subprocess.TimeoutExpired) else 'unavailable',
                             'stdout':text(getattr(exc,'stdout','')),'stderr':text(getattr(exc,'stderr',str(exc)))})
                raise
            logs.append({'stage':stage,'argv':argv,'status':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
            return result
        def cli(path: Path|None=None,frontend: bool=False):
            evidence['compiler_runs']+=1
            return process('compiler',compiler+(['--frontend'] if frontend else [])+([str(path)] if path else []))
        def good(result):
            test.assertEqual(result.returncode,0,result.stderr)
            test.assertEqual(result.stdout,'');test.assertEqual(result.stderr,'')
            test.assertTrue(xml.is_file());test.assertTrue(target.is_file())
        def run_target():
            test.assertIsNotNone(CXX,'Native target execution is required, never silently skipped')
            generated=target.read_text(encoding='utf-8')
            test.assertEqual(inspect_target(generated),())
            exe=work/('target.exe' if os.name=='nt' else 'target')
            compiled=process('target-compile',[str(CXX),'-std=c++17','-Wall','-Wextra','-pedantic',str(target),'-o',str(exe)])
            evidence['native_compiles']+=1
            test.assertEqual(compiled.returncode,0,compiled.stderr)
            executed=process('target-run',[str(exe)],5);evidence['native_runs']+=1
            test.assertEqual(executed.returncode,0,executed.stderr)
            test.assertEqual(executed.stderr,'');test.assertEqual(executed.stdout,case.stdout)
        def api_checks(text: str):
            tokens=tokenize(SourceFile(source,text))
            # The syntax sheet permits no whitespace inside a token. This
            # independent splitter/position oracle checks every token/span.
            expected=[(m.group(),m.start(),*position(text,m.start())) for m in re.finditer(r'\S+',text)]
            test.assertEqual([(t.lexeme,t.offset,t.line,t.column) for t in tokens[:-1]],expected)
            test.assertEqual((tokens[-1].line,tokens[-1].column),position(text,len(text)))
            fresh=parse(tokens,SyntaxTree(),source)
            imported=read_tree(xml);before=_record(imported)
            test.assertEqual(before,_record(fresh),'XML IDs, spellings and links must be the parser originals')
            result=compile_tree(imported,path=xml)
            test.assertEqual(before,_record(imported),'Semantic/codegen passes must not rename original XML nodes')
            test.assertEqual(result.target_source,target.read_text(encoding='utf-8'))
            names=[s.internal_name for s in result.checked.resolved.symbols.values()]
            test.assertEqual(len(names),len(set(names)))
            test.assertTrue(all(t.value!='unknown' for t in result.checked.type_by_node.values()))
            evidence['api_checks']+=1
        def rejection(result):
            test.assertEqual(result.returncode,case.status,result.stderr)
            test.assertEqual(result.stdout,'');test.assertIn(case.code,result.stderr)
            test.assertNotIn('Traceback',result.stderr)
            test.assertIsNotNone(case.fault_offset,'Each source rejection needs an independently selected fault position')
            line,col=position(case.source,case.fault_offset)
            test.assertIn(f'{source}:{line}:{col}:',result.stderr,'Wrong diagnostic token/line/column')
            if case.code=='FLOAT-INT-CONFLICT':test.assertIn('A float-integer-conflict might perhaps be possible',result.stderr)
            test.assertFalse(xml.exists());test.assertFalse(target.exists())
        try:
            if case.partner is not None:
                _checked(case.partner,source);evidence['partner_checks']+=1
            source.write_bytes(case.source.encode())
            if case.profile in ('reject','recovery','explicit-recovery'):
                if case.status>=7:
                    parse(tokenize(SourceFile(source,case.source)),SyntaxTree(),source)
                if case.profile!='reject':
                    if case.profile=='explicit-recovery':
                        names=('input with spaces.spl','-leading-name.spl','input-é.spl','nested/input.spl','long' * 30 + '.spl')
                        source=work/names[(int(case.case_id[4:])-1)%5]
                        source.parent.mkdir(parents=True,exist_ok=True)
                    source.write_bytes(f': : print ( {case.stdout} ) ; '.encode());good(cli(source))
                    source.write_bytes(case.source.encode())
                else:
                    xml.write_text('stale XML');target.write_text('stale C++')
                rejection(cli(source));test.assertEqual(source.read_bytes(),case.source.encode())
                if case.profile!='reject':
                    source.write_bytes(f': : print ( {case.stdout} ) ; '.encode());good(cli(source));run_target()
            else:
                good(cli());run_target();api_checks(case.source)
                test.assertEqual(source.read_bytes(),case.source.encode())
                if case.profile in ('execute','xml-roundtrip'):pass
                elif case.profile in ('determinism','repeated-api'):
                    original=(xml.read_bytes(),target.read_bytes())
                    good(cli(source));test.assertEqual((xml.read_bytes(),target.read_bytes()),original)
                    other=work/'other.spl';other.write_text(': : print "other" ; ')
                    _checked(other.read_text(),other)
                    api_checks(case.source)
                elif case.profile=='frontend-only':
                    invalid=': : print ( #undefined ) ; '
                    source.write_text(invalid);result=cli(source,True)
                    test.assertEqual(result.returncode,0,result.stderr);read_tree(xml).validate()
                    result=cli(source);test.assertEqual(result.returncode,7,result.stderr)
                    test.assertFalse(xml.exists());test.assertFalse(target.exists())
                elif case.profile=='xml-invalid':
                    text=xml.read_text();before=source.read_bytes()
                    # Duplicate root IDs and unknown containers must not enter
                    # semantic analysis as a successful imported program.
                    variant=(int(case.case_id[4:])-1)%5
                    mutations=(text.replace('<syntax_tree>','<syntax_tree><unexpected/>',1),
                               text.replace('<id>2</id>','<id>1</id>',1),
                               text.replace('<parent>1</parent>','<parent>999999</parent>',1),
                               text.rsplit('</syntax_tree>',1)[0],
                               text.replace('?>','?>\n<!DOCTYPE syntax_tree []>',1))
                    broken=mutations[variant]
                    test.assertNotEqual(broken,text)
                    with test.assertRaises(FoundationError):parse_tree_xml(broken,xml)
                    test.assertEqual(source.read_bytes(),before)
                elif case.profile in ('missing-input','directory-input','xml-is-directory','target-is-directory','empty-input'):
                    expected=3;code='IO-INPUT-MISSING'
                    if case.profile=='missing-input':source.unlink()
                    elif case.profile=='directory-input':source.unlink();source.mkdir();code='IO-INPUT-READ'
                    elif case.profile=='empty-input':source.write_bytes(b'');expected=5;code='SYN-EXPECTED'
                    else:
                        output=xml if case.profile=='xml-is-directory' else target
                        output.unlink();output.mkdir();expected=70;code='IO-OUTPUT-CLEAR'
                    result=cli(source);test.assertEqual(result.returncode,expected,result.stderr);test.assertIn(code,result.stderr)
                    test.assertNotIn('Traceback',result.stderr)
                    if case.profile not in ('xml-is-directory','target-is-directory'):
                        test.assertFalse(xml.exists());test.assertFalse(target.exists())
                else:
                    output=xml if case.profile.startswith(('xml-','stale-xml')) else target
                    snapshot_source=source.read_bytes()
                    if case.profile=='outputs-hardlink':
                        target.unlink();os.link(xml,target)
                        before=(xml.read_bytes(),target.read_bytes());result=cli(source)
                        test.assertEqual(result.returncode,3,result.stderr);test.assertIn('IO-OUTPUT-ALIAS',result.stderr)
                        test.assertEqual(before,(xml.read_bytes(),target.read_bytes()))
                    elif case.profile.startswith('stale-'):
                        other=work/'unrelated.data';other.write_bytes(b'preserve unrelated bytes')
                        output.unlink();output.symlink_to(other)
                        good(cli(source));test.assertEqual(other.read_bytes(),b'preserve unrelated bytes')
                    else:
                        input_path=output
                        if case.profile.endswith('hardlink'):
                            output.unlink();os.link(source,output);input_path=source
                        elif 'symlink-input' in case.profile:
                            output.unlink();output.symlink_to(source);input_path=source
                        else:output.write_bytes(snapshot_source)
                        if case.profile=='xml-relative':
                            (work/'sub').mkdir();input_path=Path('sub')/'..'/xml.name
                        before=(source.read_bytes(),xml.read_bytes(),target.read_bytes());result=cli(input_path)
                        test.assertEqual(result.returncode,3,result.stderr);test.assertIn('IO-INPUT-OUTPUT-SAME',result.stderr)
                        test.assertEqual(before,(source.read_bytes(),xml.read_bytes(),target.read_bytes()))
                    test.assertEqual(source.read_bytes(),snapshot_source)
        except Exception:
            destination=ROOT/'build'/'edge5000-failures'/case.case_id
            shutil.copytree(work,destination,dirs_exist_ok=True)
            (destination/'intended-source.spl').write_bytes(case.source.encode())
            (destination/'case.json').write_text(json.dumps(case.inventory(),indent=2)+'\n')
            (destination/'stages.json').write_text(json.dumps(logs,indent=2)+'\n')
            if case.partner:(destination/'positive-partner.spl').write_bytes(case.partner.encode())
            (destination/'reproduce.txt').write_text(f'python3 tools/run_edge_5000.py --ids {case.case_id}\n')
            raise
