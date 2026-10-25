"""Exactly 500 separately discoverable full-system tests; no generated oracle."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from tests.system500_cases import CASES, SystemCase
from tests.system500_support import exercise


class CompleteSystem500Tests(unittest.TestCase):
    """Valid inputs execute real targets; negatives verify their public phase."""


def _method(case: SystemCase):
    def run(self: CompleteSystem500Tests) -> None:
        exercise(self, case)
    run.__doc__ = f'{case.case_id}: {case.scenario}. Expected via {case.basis}.'
    return run


# Committed inventory is a review surface and must match the actual factories.
_inventory = Path(__file__).resolve().parents[1] / 'fixtures' / 'system500' / 'index.json'
if json.loads(_inventory.read_text(encoding='utf-8')) != [c.inventory() for c in CASES]:
    raise AssertionError('SYS inventory differs from cases; regenerate with tools/run_system_500.py --write-inventory')
for _case in CASES:
    setattr(CompleteSystem500Tests, f'test_{_case.case_id}_{_case.family}', _method(_case))
