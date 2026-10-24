"""Declaration identity lookup is independent of source/target spelling."""
from dataclasses import FrozenInstanceError
import unittest

from spl_frontend.codegen_ir import CodegenError, StorageRef
from spl_frontend.expansion_environment import ExpansionEnvironment


class ExpansionEnvironmentTests(unittest.TestCase):
    def test_local_parent_and_grandparent_lookup(self):
        root = ExpansionEnvironment(1, {1: StorageRef(1)})
        parent = ExpansionEnvironment(2, {2: StorageRef(2)}, root)
        child = ExpansionEnvironment(3, {3: StorageRef(3)}, parent)
        self.assertEqual(child.resolve(1), StorageRef(1))
        self.assertEqual(child.resolve(2), StorageRef(2))
        self.assertEqual(child.resolve(3), StorageRef(3))

    def test_repeated_parent_instances_capture_current_storage(self):
        first = ExpansionEnvironment(2, {9: StorageRef(4)})
        second = ExpansionEnvironment(2, {9: StorageRef(5)})
        self.assertEqual(ExpansionEnvironment(3, {}, first).resolve(9), StorageRef(4))
        self.assertEqual(ExpansionEnvironment(3, {}, second).resolve(9), StorageRef(5))

    def test_same_spelling_declarations_are_distinguished_by_identity(self):
        env = ExpansionEnvironment(2, {7: StorageRef(6)}, ExpansionEnvironment(1, {4: StorageRef(7)}))
        self.assertNotEqual(env.resolve(7), env.resolve(4))

    def test_input_mapping_is_copied_and_result_read_only(self):
        bindings = {1: StorageRef(8)}
        env = ExpansionEnvironment(1, bindings)
        bindings[1] = StorageRef(9)
        self.assertEqual(env.resolve(1), StorageRef(8))
        with self.assertRaises(TypeError):
            env.storage_by_symbol[2] = StorageRef(10)
        with self.assertRaises(FrozenInstanceError):
            env.scope_id = 4

    def test_missing_capture_reports_invariant_error(self):
        with self.assertRaises(CodegenError) as raised:
            ExpansionEnvironment(1).resolve(5)
        self.assertEqual(raised.exception.code, "GEN-UNBOUND-CAPTURE")

    def test_invalid_ids_and_mapping_values_rejected(self):
        for scope in (True, 0, -1, 1.0):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                ExpansionEnvironment(scope)
        with self.assertRaises(ValueError):
            ExpansionEnvironment(1, {True: StorageRef(8)})
        with self.assertRaises(ValueError):
            ExpansionEnvironment(1, {1: "spl_one"})
        with self.assertRaises(ValueError):
            ExpansionEnvironment(1).resolve(True)

    def test_malformed_parent_cycle_does_not_loop(self):
        env = ExpansionEnvironment(1)
        object.__setattr__(env, "parent", env)
        with self.assertRaises(CodegenError) as raised:
            env.resolve(1)
        self.assertEqual(raised.exception.code, "GEN-ENV-CYCLE")
