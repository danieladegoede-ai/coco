"""Invariant tests for typed target IR and structural cloning."""

import unittest

from spl_frontend.codegen_ir import (
    Assign,
    BinaryAssign,
    BinaryOperator,
    CodeMineSection,
    CodegenError,
    Comment,
    FreshNameAllocator,
    IRFragment,
    Jump,
    Label,
    LabelRef,
    NumberLiteral,
    PrintString,
    StorageKind,
    StorageRef,
    StringLiteral,
    SymbolRef,
    TargetProgram,
    TargetScalarType,
    clone_fragment,
)
from spl_frontend.semantic_model import NumericMode
from tests.codegen_support import checked_source


def empty_target(fragment: IRFragment, *, mode=NumericMode.INTEGER, code_mine=()) -> TargetProgram:
    checked = checked_source(": : ")
    root = checked.resolved.tree.root
    assert root is not None
    p_id = root.child_ids[0]
    scope_id = checked.resolved.scope_by_node[p_id]
    return TargetProgram(mode, scope_id, checked.resolved.symbols, (), fragment, tuple(code_mine))


class FreshNameAllocatorTests(unittest.TestCase):
    def test_allocation_is_deterministic_and_scoped_to_instance(self):
        left = FreshNameAllocator()
        right = FreshNameAllocator()
        self.assertEqual(left.new_label(), LabelRef(1))
        self.assertEqual(left.new_label(), LabelRef(2))
        self.assertEqual(right.new_label(), LabelRef(1))
        temp = left.new_temporary(TargetScalarType.INTEGER)
        expansion = left.new_expansion_storage(TargetScalarType.INTEGER)
        capture = left.new_capture(TargetScalarType.INTEGER)
        ret = left.new_return_storage(TargetScalarType.INTEGER)
        self.assertEqual(
            [FreshNameAllocator.storage_name(item) for item in (temp, expansion, capture, ret)],
            ["spl_tmp_1", "spl_exp_1", "spl_cap_1", "spl_ret_1"],
        )
        self.assertEqual(FreshNameAllocator.label_name(LabelRef(1)), "spl_lbl_1")
        self.assertEqual(right.new_temporary(TargetScalarType.INTEGER).storage_id, 1)

    def test_storage_identity_includes_namespace_and_type(self):
        temporary = StorageRef(1, StorageKind.TEMPORARY, TargetScalarType.INTEGER)
        expansion = StorageRef(1, StorageKind.EXPANSION, TargetScalarType.INTEGER)
        floating = StorageRef(1, StorageKind.TEMPORARY, TargetScalarType.FLOAT)
        self.assertEqual(len({temporary, expansion, floating}), 3)

    def test_invalid_fresh_identity_is_rejected(self):
        with self.assertRaises(CodegenError):
            StorageRef(0)
        with self.assertRaises(CodegenError):
            LabelRef(-1)


class FragmentCloningTests(unittest.TestCase):
    def test_clone_remaps_declared_storage_and_defined_labels_only(self):
        source_storage = StorageRef(1, StorageKind.TEMPORARY, TargetScalarType.INTEGER)
        local_label = LabelRef(1)
        external_label = LabelRef(2)
        source = IRFragment(
            (source_storage,),
            (
                Label(local_label),
                Assign(source_storage, NumberLiteral("7")),
                PrintString(StringLiteral("spl_tmp_1 #x else not")),
                Comment("spl_tmp_10 must remain text; #x is not a lookup"),
                Jump(local_label),
                Jump(external_label),
            ),
        )
        clone = clone_fragment(source, FreshNameAllocator())
        self.assertNotEqual(clone.declarations[0], source_storage)
        self.assertGreater(clone.declarations[0].storage_id, source_storage.storage_id)
        clone_local = next(item.label for item in clone.instructions if isinstance(item, Label))
        self.assertNotEqual(clone_local, local_label)
        self.assertEqual(next(item for item in clone.instructions if isinstance(item, PrintString)), source.instructions[2])
        self.assertEqual(next(item for item in clone.instructions if isinstance(item, Comment)), source.instructions[3])
        jumps = [item for item in clone.instructions if isinstance(item, Jump)]
        self.assertEqual(jumps[0].target, clone_local)
        self.assertEqual(jumps[1].target, external_label)

    def test_explicit_remap_destinations_are_reserved_before_future_allocation(self):
        original = StorageRef(1, StorageKind.TEMPORARY, TargetScalarType.INTEGER)
        fragment = IRFragment((original,), (Assign(original, NumberLiteral("1")),))
        allocator = FreshNameAllocator()
        replacement = StorageRef(8, StorageKind.TEMPORARY, TargetScalarType.INTEGER)
        clone = clone_fragment(fragment, allocator, storage_remap={original: replacement})
        self.assertEqual(clone.declarations, (replacement,))
        self.assertEqual(allocator.new_temporary(TargetScalarType.INTEGER).storage_id, 9)

    def test_storage_remap_cannot_change_numeric_scalar_type(self):
        original = StorageRef(1, StorageKind.TEMPORARY, TargetScalarType.INTEGER)
        replacement = StorageRef(2, StorageKind.TEMPORARY, TargetScalarType.FLOAT)
        with self.assertRaisesRegex(CodegenError, "cannot change scalar type"):
            clone_fragment(
                IRFragment((original,), (Assign(original, NumberLiteral("1")),)),
                FreshNameAllocator(),
                storage_remap={original: replacement},
            )

    def test_clone_applies_symbol_remap_by_identity_without_text_substitution(self):
        fragment = IRFragment(instructions=(
            Assign(StorageRef(1), SymbolRef(20)),
            PrintString(StringLiteral("#x #xy #x2")),
        ))
        remapped = StorageRef(5, StorageKind.EXPANSION, TargetScalarType.INTEGER)
        clone = clone_fragment(
            fragment,
            FreshNameAllocator(),
            symbol_remap={20: remapped},
            storage_remap={StorageRef(1): StorageRef(7)},
        )
        assign = clone.instructions[0]
        self.assertEqual(assign.target, StorageRef(7))
        self.assertEqual(assign.value, remapped)
        self.assertEqual(clone.instructions[1].value.value, "#x #xy #x2")

    def test_duplicate_local_labels_cannot_be_cloned(self):
        label = LabelRef(1)
        fragment = IRFragment(instructions=(Label(label), Label(label)))
        with self.assertRaisesRegex(CodegenError, "duplicate labels"):
            clone_fragment(fragment, FreshNameAllocator())


class ClosedProgramValidationTests(unittest.TestCase):
    def test_numeric_operators_and_literals_must_match_selected_mode(self):
        for mode, instruction, message in (
            (NumericMode.INTEGER, Assign(StorageRef(1), NumberLiteral("1.5")), "decimal literal"),
            (NumericMode.INTEGER, BinaryAssign(StorageRef(1), BinaryOperator.DIVIDE,
                                             NumberLiteral("5"), NumberLiteral("2")), "Division"),
            (NumericMode.FLOAT, BinaryAssign(StorageRef(1, value_type=TargetScalarType.FLOAT), BinaryOperator.MODULO,
                                           NumberLiteral("5"), NumberLiteral("2")), "Modulo"),
        ):
            with self.subTest(mode=mode, instruction=instruction), self.assertRaisesRegex(CodegenError, message):
                empty_target(IRFragment((instruction.target,), (instruction,)), mode=mode)

    def test_unknown_jump_label_is_rejected(self):
        with self.assertRaisesRegex(CodegenError, "IR-UNKNOWN-LABEL|not defined"):
            empty_target(IRFragment(instructions=(Jump(LabelRef(99)),)))

    def test_duplicate_labels_are_rejected(self):
        repeated = LabelRef(1)
        with self.assertRaisesRegex(CodegenError, "defined more than once"):
            empty_target(IRFragment(instructions=(Label(repeated), Label(repeated))))

    def test_undeclared_temporary_is_rejected(self):
        with self.assertRaisesRegex(CodegenError, "used but not declared"):
            empty_target(IRFragment(instructions=(Assign(StorageRef(9), NumberLiteral("1")),)))

    def test_storage_type_must_match_selected_numeric_mode(self):
        floating = StorageRef(1, StorageKind.TEMPORARY, TargetScalarType.FLOAT)
        with self.assertRaisesRegex(CodegenError, "requires int"):
            empty_target(IRFragment((floating,), (Assign(floating, NumberLiteral("1")),)))

    def test_code_mine_payload_is_typed_and_non_executable_metadata(self):
        program = empty_target(IRFragment(), code_mine=(CodeMineSection("template #f", "*/ else not"),))
        self.assertEqual(program.code_mine[0].text, "*/ else not")

    def test_malformed_numeric_literals_are_rejected_before_rendering(self):
        for literal in ("", "1; system(0)", "NaN", "1.2.3", "#x", "-0", "01", "1.0", ".5", "1."):
            with self.subTest(literal=literal), self.assertRaises(CodegenError):
                NumberLiteral(literal)


if __name__ == "__main__":
    unittest.main()
