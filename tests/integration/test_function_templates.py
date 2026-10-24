"""Public template handoff and clone/remap contracts using actual C++ execution.

Explicit test instantiation demonstrates the #29 interface for the future
inliner; this fixture does not install call expansion into the public CLI.
"""
from dataclasses import replace
import unittest

from spl_frontend.codegen import CodegenContext, generate_target
from spl_frontend.codegen_ir import (
    Assign, IRFragment, Label, NumberLiteral, PrintNumber, PrintString,
    StringLiteral, clone_fragment, combine_fragments,
)
from spl_frontend.function_templates import prepare_function_templates
from spl_frontend.target_writer import render_target
from tools.target_inspector import inspect_target
from tests.codegen_support import TARGET_CXX, compile_and_run_target
from tests.unit.test_function_templates import checked


@unittest.skipUnless(TARGET_CXX, "C++ compiler required for template execution checks")
class FunctionTemplateIntegrationTests(unittest.TestCase):
    def run_target(self, program, expected):
        target = render_target(program)
        self.assertEqual(inspect_target(target), ())
        _, result = compile_and_run_target(target)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected, ""))
        return target

    def test_uncalled_templates_and_inner_annotations_remain_non_executable(self):
        source = checked('#x : void #unused ( ) { : : #x = 99 ; print "bad" ; '
                         'nop ; comment "inside.mine" ; return } : #x = 4 ; print ( #x ) ; ')
        prepared = prepare_function_templates(source)
        program = replace(generate_target(source), code_mine=prepared.code_mine)
        target = self.run_target(program, "4")
        self.assertIn("//     // nop", target)
        self.assertIn("BEGIN CODE MINE", target)

    def test_cloned_parent_templates_capture_current_instance_and_keep_globals(self):
        source = checked('#x : num #f ( #a ) { #x : void #child ( ) { : : '
                         '#x = add ( #x 1 ) ; return } : #x = #a ; #child ( ) ; '
                         'return ( #x ) } : #x = 90 ; ')
        context = CodegenContext(source)
        prepared = prepare_function_templates(source, context=context)
        parent = next(t for i, t in prepared.templates.items()
                      if source.resolved.symbols[i].original_name == "#f")
        before = (parent.declarations, parent.instructions, dict(parent.storage_by_symbol))
        program = generate_target(source, context=context)
        root = next(s for s in source.resolved.symbols.values()
                    if s.original_name == "#x" and s.scope_id == program.root_scope_id)
        from spl_frontend.codegen_ir import SymbolRef
        fragments = [program.fragment]
        for value in (4, 8):
            mapping = {slot: context.allocator.new_storage(slot.kind, slot.value_type)
                       for slot in parent.declarations}
            cloned = clone_fragment(IRFragment(parent.declarations, parent.instructions),
                                    context.allocator, storage_remap=mapping)
            formal = mapping[parent.storage_by_symbol[parent.formal_symbol_ids[0]]]
            fragments.extend((IRFragment(instructions=(Assign(formal, NumberLiteral(str(value))),)),
                              cloned, IRFragment(instructions=(PrintNumber(mapping[parent.return_storage]),
                                                               PrintString(StringLiteral(":"))))))
        fragments.append(IRFragment(instructions=(PrintNumber(SymbolRef(root.symbol_id)),)))
        self.run_target(replace(program, fragment=combine_fragments(*fragments),
                                code_mine=prepared.code_mine), "5:9:90")
        self.assertEqual(before, (parent.declarations, parent.instructions, dict(parent.storage_by_symbol)))

    def test_repeated_loop_clones_have_disjoint_storage_and_labels(self):
        source = checked(': num #f ( #n ) { #i : : #i = 0 ; while lesser ( #i #n ) '
                         'do { #i = add ( #i 1 ) ; } ; return ( #i ) } : ')
        context = CodegenContext(source)
        prepared = prepare_function_templates(source, context=context)
        template = next(iter(prepared.templates.values()))
        pieces = []
        definitions = []
        slots = []
        for value in (2, 3):
            mapping = {s: context.allocator.new_storage(s.kind, s.value_type) for s in template.declarations}
            clone = clone_fragment(IRFragment(template.declarations, template.instructions), context.allocator,
                                   storage_remap=mapping)
            pieces.extend((IRFragment(instructions=(Assign(mapping[template.storage_by_symbol[template.formal_symbol_ids[0]]], NumberLiteral(str(value))),)),
                           clone, IRFragment(instructions=(PrintNumber(mapping[template.return_storage]),))))
            definitions.append({i.label for i in clone.instructions if isinstance(i, Label)})
            slots.append(set(clone.declarations))
        self.assertTrue(definitions[0])
        self.assertTrue(definitions[0].isdisjoint(definitions[1]))
        self.assertTrue(slots[0].isdisjoint(slots[1]))
        program = replace(generate_target(source, context=context), fragment=combine_fragments(*pieces),
                          code_mine=prepared.code_mine)
        self.run_target(program, "23")
