"""Run the 500 public unittest methods in bounded parallel, or inspect inventory.

Do not run the old suite concurrently: historical tests temporarily change cwd.
The new cases use subprocess cwd and independent temporary directories only.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from tests.system500_cases import CASES, SystemCase


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-inventory', action='store_true')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--report', type=Path, default=ROOT/'build'/'system500-report.json')
    parser.add_argument('--ids', nargs='+', help='Optional SYS IDs for a focused run')
    args = parser.parse_args()
    inventory = [case.inventory() for case in CASES]
    if args.write_inventory:
        path = ROOT/'tests'/'fixtures'/'system500'/'index.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf-8')
        print(f'Wrote {len(inventory)} distinct source cases: {dict(Counter(c.family for c in CASES))}')
        return 0
    if not 1 <= args.workers <= 8:
        parser.error('--workers must be between 1 and 8')
    selected = [c for c in CASES if args.ids is None or c.case_id in args.ids]
    if args.ids and set(args.ids) != {c.case_id for c in selected}:
        parser.error('Unknown case ID')
    from tests.integration.test_system_500 import CompleteSystem500Tests
    def run(case: SystemCase) -> dict:
        started=time.monotonic()
        test=CompleteSystem500Tests(f'test_{case.case_id}_{case.family}')
        result=unittest.TestResult()
        test.run(result)
        return {'id':case.case_id,'family':case.family,'passed':result.wasSuccessful(),
                'tests_run':result.testsRun,'skipped':result.skipped,
                'elapsed_seconds':round(time.monotonic()-started,3),
                'failures':[text for _,text in result.failures+result.errors]}
    started=time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results=list(pool.map(run,selected))
    report={'cases':len(results),'passed':sum(r['passed'] for r in results),
            'elapsed_seconds':round(time.monotonic()-started,3),'results':results}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    for result in results:
        if not result['passed']:
            print(result['id'],*result['failures'],sep='\n')
    print(f"{report['passed']}/{report['cases']} passed in {report['elapsed_seconds']}s; {args.report}")
    return 0 if report['passed']==report['cases'] else 1


if __name__=='__main__':
    raise SystemExit(main())
