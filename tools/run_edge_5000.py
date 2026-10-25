"""Run the baseline serially and/or 5,000 isolated edge cases in bounded threads.

Normal unittest discovery includes every new method too. The bounded runner
avoids serial native-compiler overhead and can partition edges into CI shards.
"""
from __future__ import annotations
import argparse
import hashlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from tests.edge5000.cases import CASES


def flatten(suite):
    for case in suite:
        if isinstance(case,unittest.TestSuite):yield from flatten(case)
        else:yield case


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',choices=('all','baseline','edges'),default='edges')
    parser.add_argument('--workers',type=int,default=6)
    parser.add_argument('--shard-index',type=int,default=0)
    parser.add_argument('--shard-count',type=int,default=1)
    parser.add_argument('--ids',nargs='+')
    parser.add_argument('--executable',type=Path,help='Run edge CLI stages through this exact packaged binary')
    parser.add_argument('--report',type=Path,default=ROOT/'build'/'edge5000-report.json')
    parser.add_argument('--write-inventory',action='store_true')
    args=parser.parse_args()
    if args.write_inventory:
        old={row['source_sha256'] for row in json.loads((ROOT/'tests'/'fixtures'/'system500'/'index.json').read_text())}
        assert not old.intersection(c.inventory()['source_sha256'] for c in CASES),'Repeats the previous 500 corpus'
        path=ROOT/'tests'/'fixtures'/'edge5000'/'index.jsonl';path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(''.join(json.dumps(c.inventory(),separators=(',',':'))+'\n' for c in CASES),encoding='utf-8')
        print('5000 unique new sources:',dict(Counter(c.family for c in CASES)));return 0
    if not 1<=args.workers<=8:parser.error('workers must be 1..8')
    if args.shard_count<1 or not 0<=args.shard_index<args.shard_count:parser.error('invalid shard')
    selected=[c for i,c in enumerate(CASES) if i%args.shard_count==args.shard_index and (args.ids is None or c.case_id in args.ids)]
    if args.ids and set(args.ids)!={c.case_id for c in selected}:parser.error('unknown ID or ID outside selected shard')
    if args.suite!='baseline' and not selected:parser.error('empty test selection')
    executable=args.executable.resolve() if args.executable else None
    if executable is not None and not executable.is_file():parser.error('packaged executable does not exist')
    executable_hash=hashlib.sha256(executable.read_bytes()).hexdigest() if executable else None
    report={'executable':str(executable) if executable else None,'executable_sha256':executable_hash,'platform':platform.platform(),'python':sys.version,'workers':args.workers,
            'shard_index':args.shard_index,'shard_count':args.shard_count,'baseline':None,'results':[]}
    cxx=shutil.which('c++') or shutil.which('g++') or shutil.which('clang++')
    report['target_compiler']=cxx
    if cxx:
        report['target_compiler_version']=subprocess.run([cxx,'--version'],capture_output=True,text=True,timeout=10).stdout.splitlines()[0]
    start=time.monotonic()
    if args.suite in ('all','baseline'):
        suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
        edge_prefixes=('edge5000.test_matrix.Edge5000Tests.','tests.edge5000.test_matrix.Edge5000Tests.')
        baseline=unittest.TestSuite(c for c in flatten(suite) if not c.id().startswith(edge_prefixes))
        result=unittest.TextTestRunner(verbosity=2).run(baseline)
        report['baseline']={'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful() and not result.skipped}
    if args.suite!='baseline':
        from tests.edge5000.test_matrix import Edge5000Tests
        def run(case):
            tick=time.monotonic();test=Edge5000Tests(f'test_{case.case_id}_{case.family}')
            if executable:test.compiler_command=[str(executable)]
            result=unittest.TestResult();test.run(result)
            return {'id':case.case_id,'family':case.family,'passed':result.wasSuccessful() and not result.skipped,
                    'run':result.testsRun,'skipped':result.skipped,'elapsed':round(time.monotonic()-tick,3),
                    'evidence':getattr(test,'edge_evidence',{}),'failures':[v for _,v in result.errors+result.failures]}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            pending=[pool.submit(run,c) for c in selected];last=time.monotonic()
            for future in as_completed(pending):
                row=future.result();report['results'].append(row)
                if not row['passed']:print('FAIL',row['id'],*row['failures'],flush=True)
                if time.monotonic()-last>=15:
                    print(f"Edges {len(report['results'])}/{len(selected)}; failures {sum(not x['passed'] for x in report['results'])}",flush=True);last=time.monotonic()
    if executable and hashlib.sha256(executable.read_bytes()).hexdigest()!=executable_hash:raise RuntimeError('Packaged binary changed during testing')
    report['results'].sort(key=lambda r:r['id'])
    report['elapsed_seconds']=round(time.monotonic()-start,3)
    report['edge_run']=len(report['results']);report['edge_passed']=sum(r['passed'] for r in report['results'])
    report['evidence_totals']=dict(Counter({key:sum(r['evidence'].get(key,0) for r in report['results']) for key in ('compiler_runs','native_compiles','native_runs','partner_checks','api_checks')}))
    report['passed']=all(r['passed'] for r in report['results']) and (report['baseline'] is None or report['baseline']['passed'])
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f"Edges {report['edge_passed']}/{report['edge_run']}; baseline {report['baseline']}; {report['elapsed_seconds']}s; {args.report}",flush=True)
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
