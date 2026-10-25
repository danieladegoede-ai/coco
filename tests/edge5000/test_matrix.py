"""5,000 separately named tests. Factories carry the source and expectations."""
from __future__ import annotations
import json
from pathlib import Path
import unittest
from tests.edge5000.cases import CASES,EdgeCase
from tests.edge5000.support import exercise


class Edge5000Tests(unittest.TestCase):
    """Execute full source/target cases or deliberately reject invalid source."""


def method(case: EdgeCase):
    def run(self: Edge5000Tests) -> None:
        exercise(self,case,compiler_command=getattr(self,'compiler_command',None))
    run.__doc__=case.scenario
    return run


inventory=Path(__file__).parents[1]/'fixtures'/'edge5000'/'index.jsonl'
if [json.loads(line) for line in inventory.read_text(encoding='utf-8').splitlines()] != [c.inventory() for c in CASES]:
    raise AssertionError('Edge inventory is stale; run tools/run_edge_5000.py --write-inventory')
for case in CASES:setattr(Edge5000Tests,f'test_{case.case_id}_{case.family}',method(case))
