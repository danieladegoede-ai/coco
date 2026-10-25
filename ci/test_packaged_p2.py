"""Validate an exact native compiler outside the checkout and record its hash."""
from __future__ import annotations
from dataclasses import asdict
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from tools.test_semantic_acceptance import run_manifest as semantic_manifest
from tools.test_generated_target import run_manifest as target_manifest
from tools.build_native import binary_identity


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--executable',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True)
    p.add_argument('--target-compiler')
    args=p.parse_args();original=args.executable.resolve()
    expected_hash=hashlib.sha256(original.read_bytes()).hexdigest()
    report={'executable_sha256':expected_hash,'native_identity':binary_identity(original)}
    with tempfile.TemporaryDirectory(prefix='packaged P2 clean ') as directory:
        work=Path(directory);exe=work/original.name;shutil.copy2(original,exe)
        source=(ROOT/'release'/'example.spl').read_bytes();(work/'SPL.txt').write_bytes(source)
        env=dict(os.environ);env['PYTHONPATH']='';env['PYTHONHOME']=str(work/'no Python installed')
        env['PATH']=os.pathsep.join((str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32'),os.environ.get('SystemRoot','C:/Windows'))) if os.name=='nt' else '/usr/bin:/bin'
        result=subprocess.run([str(exe)],cwd=work,env=env,capture_output=True,text=True,encoding='utf-8',timeout=60)
        report['clean_launch']={'status':result.returncode,'stdout':result.stdout,'stderr':result.stderr,
                                'checkout_files_present':False,'pythonpath_empty':True,'pythonhome_unavailable':True}
        if result.returncode or result.stdout or result.stderr or not (work/'tree.xml').is_file() or not (work/'program.cpp').is_file():
            raise AssertionError(f'Packaged clean launch failed: {report["clean_launch"]}')
        semantics,summary=semantic_manifest(compiler_command=[str(exe),'{input}'],timeout=60,artifacts=ROOT/'build'/'packaged-semantic-failures')
        report['semantic_summary']=summary;report['semantic_reports']=[asdict(row) for row in semantics]
        targets,summary=target_manifest(ROOT/'tests/fixtures/codegen/acceptance/cases.json',compiler_command=[str(exe)],
                                       target_compiler=args.target_compiler,timeout=60,artifacts=ROOT/'build'/'packaged-target-failures')
        report['target_summary']=summary;report['target_reports']=[r.to_json() for r in targets]
        blackbox=subprocess.run([sys.executable,str(ROOT/'tools/black_box_test.py'),'--executable',str(exe)],cwd=ROOT,capture_output=True,text=True,timeout=300)
        report['blackbox']={'status':blackbox.returncode,'stdout':blackbox.stdout,'stderr':blackbox.stderr}
    report['unchanged_binary']=hashlib.sha256(original.read_bytes()).hexdigest()==expected_hash
    report['passed']=(report['unchanged_binary'] and all(r.passed for r in semantics) and all(r.passed for r in targets) and blackbox.returncode==0)
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:val for key,val in report.items() if not key.endswith('_reports')},indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
