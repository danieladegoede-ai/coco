"""Ten native representation anchors, separate from the 5,000-case matrix.

These document the current D05 int32/binary32 target behavior. The course
sources do not settle overflow or arbitrary-precision policies; no overflowing
arithmetic, INT_MIN/-1 division/remainder, or new source restriction is used.
"""
from __future__ import annotations
import unittest
from tools.test_generated_target import verify_case


BOUNDARIES = (
    ('NB01_int_max', ': : print ( 2147483647 ) ; ', '2147483647'),
    ('NB02_int_min', ': : print ( -2147483648 ) ; ', '-2147483648'),
    ('NB03_add_to_max', ': : print ( add ( 2147483646 1 ) ) ; ', '2147483647'),
    ('NB04_sub_to_min', ': : print ( sub ( -2147483647 1 ) ) ; ', '-2147483648'),
    ('NB05_min_remainder', ': : print ( mod ( -2147483648 7 ) ) ; ', '-2'),
    ('NB06_negate_max', ': : print ( neg ( 2147483647 ) ) ; ', '-2147483647'),
    ('NB07_binary32_cancel', '#x #mode : : #mode = div ( 1 1 ) ; #x = 16777217 ; print ( sub ( #x 16777216 ) ) ; ', '0'),
    ('NB08_binary32_difference', '#x #mode : : #mode = div ( 1 1 ) ; #x = 16777217 ; print ( sub ( #x 16777215 ) ) ; ', '1'),
    ('NB09_binary32_fraction_equality', ': : if eq ( add ( 0.1 0.2 ) 0.3 ) then { print "t" ; } else { print "f" ; } ; ', 't'),
    ('NB10_exact_negative_fraction', ': : print ( sub ( 0.25 1 ) ) ; ', '-0.75'),
)


class NumericBoundaryTests(unittest.TestCase):
    """Expected values calculated independently of compiler/model implementation."""


def _method(case_id: str, source: str, output: str):
    def test(self: NumericBoundaryTests) -> None:
        report = verify_case(source,output,case_id=case_id,timeout=30)
        self.assertTrue(report.passed,report.to_json())
        self.assertEqual(report.compiler_status,0)
        self.assertEqual(report.target_compile_status,0)
        self.assertEqual(report.execution_status,0)
    return test


for _id,_source,_stdout in BOUNDARIES:
    setattr(NumericBoundaryTests,f'test_{_id}',_method(_id,_source,_stdout))
