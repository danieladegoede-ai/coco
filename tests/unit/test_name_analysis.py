"""Part 2a rules exercised through the real lexer/parser and public name pass."""

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import io
from pathlib import Path
import unittest

from spl_frontend.lexer import tokenize
from spl_frontend.name_analysis import (
    NameAnalysisError, build_call_hierarchy, resolve_names,
)
from spl_frontend.parser import parse
from spl_frontend.semantic_model import (
    FoundationError, ResolvedProgram, SemanticType, SourceSpan, SymbolKind,
)
from spl_frontend.source import SourceFile
from spl_frontend.source_map import SourceMap, build_source_map
from spl_frontend.tree import NodeKind, SyntaxTree
from spl_frontend.tree_walkers import iter_preorder


PATH = Path("names.spl")


def parsed(text):
    tokens = tokenize(SourceFile(PATH, text))
    tree = parse(tokens, SyntaxTree(), PATH)
    return tree, build_source_map(tree, tokens, PATH)


def resolve(text):
    tree, locations = parsed(text)
    return resolve_names(tree, locations)


def named(program, spelling, kind=None):
    return [s for s in program.symbols.values()
            if s.original_name == spelling and (kind is None or s.kind is kind)]


def occurrences(program, spelling):
    return [n for n in iter_preorder(program.tree)
            if n.kind is NodeKind.LEAF and n.contents == spelling]


class NameAnalysisTests(unittest.TestCase):
    def assert_name_error(self, text, code, name):
        with self.assertRaises(NameAnalysisError) as raised:
            resolve(text)
        error = raised.exception
        self.assertEqual(error.code, code)
        self.assertEqual(error.name, name)
        self.assertIsNotNone(error.span)
        self.assertEqual(error.path, PATH)
        self.assertIn(name, error.render())
        self.assertTrue(error.rule)
        self.assertTrue(error.hint)
        return error

    def test_empty_program_has_one_scope_and_complete_annotations(self):
        result = resolve(": : ")
        self.assertEqual(len(result.scopes), 1)
        self.assertFalse(result.symbols)
        self.assertEqual(set(result.scope_by_node), {n.node_id for n in result.tree.iter_nodes()})
        self.assertEqual(set(result.scope_by_node.values()), {1})

    def test_global_read_write_and_repeated_occurrences_share_one_identity(self):
        result = resolve('#x : : #x = add ( #x 1 ) ; print ( #x ) ; ')
        symbol, = named(result, "#x")
        self.assertEqual(symbol.internal_name, "spl_v1")
        self.assertEqual(symbol.value_type, SemanticType.UNKNOWN)
        self.assertEqual(len(occurrences(result, "#x")), 4)
        for node in occurrences(result, "#x"):
            self.assertEqual(result.binding_by_name_node[node.node_id], symbol.symbol_id)
            self.assertEqual(result.renamed_name_by_node[node.node_id], symbol.internal_name)

    def test_current_outer_global_and_nearest_shadowing(self):
        result = resolve(
            '#x #global : void #f ( #p ) { #x #outer : '
            'void #g ( ) { #local : : '
            '#local = add ( #x #outer ) ; #global = #p ; return } '
            ': #g ( ) ; return } : #f ( 1 ) ; '
        )
        global_x, outer_x = named(result, "#x")
        x_nodes = occurrences(result, "#x")
        self.assertEqual(result.binding_by_name_node[x_nodes[-1].node_id], outer_x.symbol_id)
        self.assertNotEqual(global_x.internal_name, outer_x.internal_name)
        for spelling in ("#global", "#outer", "#local", "#p"):
            symbol, = named(result, spelling)
            self.assertEqual({result.binding_by_name_node[n.node_id]
                              for n in occurrences(result, spelling)}, {symbol.symbol_id})
        self.assertEqual([s.depth for s in result.scopes.values()], [0, 1, 2])

    def test_sibling_locals_with_same_spelling_are_distinct(self):
        result = resolve(
            ': void #f ( ) { #x : : #x = 1 ; return } '
            'void #g ( ) { #x : : #x = 2 ; return } '
            ': #f ( ) ; #g ( ) ; '
        )
        left, right = named(result, "#x")
        self.assertNotEqual(left.scope_id, right.scope_id)
        self.assertEqual(result.scopes[left.scope_id].depth, result.scopes[right.scope_id].depth)
        self.assertNotEqual(left.internal_name, right.internal_name)
        self.assertEqual([result.binding_by_name_node[n.node_id] for n in occurrences(result, "#x")],
                         [left.symbol_id, left.symbol_id, right.symbol_id, right.symbol_id])

    def test_third_sibling_cannot_read_other_siblings_local(self):
        self.assert_name_error(
            ': void #f ( ) { #x : : return } void #g ( ) { #x : : return } '
            'void #h ( ) { : : print ( #x ) ; return } : ',
            "NAME-UNDECLARED-VARIABLE", "#x",
        )

    def test_announcement_21_cousin_uses_ancestor_not_sideways_declaration(self):
        template = (
            '{globals} : void #f ( ) { : '
            'void #g ( ) { #x : void #j ( ) { : : print ( #x ) ; return } : return } '
            'void #h ( ) { : void #k ( ) { : : print ( #x ) ; return } : return } '
            ': return } : '
        )
        self.assert_name_error(template.replace("{globals}", ""), "NAME-UNDECLARED-VARIABLE", "#x")
        result = resolve(template.replace("{globals}", "#x"))
        global_x, g_x = named(result, "#x")
        self.assertEqual([result.binding_by_name_node[n.node_id] for n in occurrences(result, "#x")],
                         [global_x.symbol_id, g_x.symbol_id, g_x.symbol_id, global_x.symbol_id])

    def test_child_local_and_parameter_may_shadow_ancestor_parameter(self):
        for child_header in ('#x : : #x = 1 ;', ': : #x = 1 ;'):
            with self.subTest(child_header=child_header):
                params = '' if child_header.startswith('#x') else '#x'
                result = resolve(
                    f': void #f ( #x ) {{ : void #g ( {params} ) {{ {child_header} return }} '
                    ': return } : '
                )
                outer, inner = named(result, "#x")
                self.assertNotEqual(outer.internal_name, inner.internal_name)
                self.assertEqual(result.binding_by_name_node[occurrences(result, "#x")[-1].node_id], inner.symbol_id)

    def test_duplicate_locals_and_parameters_and_parameter_masking(self):
        for text, code in (
            ('#x #x : : ', "NAME-DUPLICATE-VARIABLE"),
            (': void #f ( #x #x ) { : : return } : ', "NAME-DUPLICATE-PARAMETER"),
            (': void #f ( #x ) { #x : : return } : ', "NAME-PARAMETER-MASK"),
        ):
            with self.subTest(code=code):
                error = self.assert_name_error(text, code, "#x")
                self.assertIsNotNone(error.related_node_id)
                self.assertLess(error.related_span.offset, error.span.offset)

    def test_duplicate_nested_locals_fail_even_in_uncalled_function(self):
        self.assert_name_error(': void #f ( ) { #x #x : : return } : ',
                               "NAME-DUPLICATE-VARIABLE", "#x")

    def test_duplicate_functions_reject_overloading_by_parameters_or_return_type(self):
        for second in ('void #f ( ) { : : return }',
                       'void #f ( #a ) { : : return }',
                       'num #f ( ) { : : return ( 1 ) }'):
            with self.subTest(second=second):
                self.assert_name_error(f': void #f ( ) {{ : : return }} {second} : ',
                                       "NAME-DUPLICATE-FUNCTION", "#f")

    def test_duplicate_functions_are_checked_in_nested_declaration_lists(self):
        self.assert_name_error(
            ': void #f ( ) { : void #g ( ) { : : return } '
            'void #g ( ) { : : return } : return } : ',
            "NAME-DUPLICATE-FUNCTION", "#g",
        )

    def test_separate_scopes_may_each_declare_same_helper_name(self):
        result = resolve(
            ': void #f ( ) { : void #h ( ) { : : return } : #h ( ) ; return } '
            'void #g ( ) { : void #h ( ) { : : return } : #h ( ) ; return } '
            ': #f ( ) ; #g ( ) ; '
        )
        helpers = named(result, "#h")
        self.assertEqual(len({s.internal_name for s in helpers}), 2)
        self.assertEqual([result.binding_by_name_node[n.node_id] for n in occurrences(result, "#h")],
                         [helpers[0].symbol_id] * 2 + [helpers[1].symbol_id] * 2)

    def test_child_with_same_name_as_parent_is_a_distinct_legal_call(self):
        result = resolve(': void #f ( ) { : void #f ( ) { : : return } : #f ( ) ; return } : #f ( ) ; ')
        parent, child = named(result, "#f")
        self.assertEqual([result.binding_by_name_node[n.node_id] for n in occurrences(result, "#f")],
                         [parent.symbol_id, child.symbol_id, child.symbol_id, parent.symbol_id])

    def test_direct_child_calls_succeed_in_both_declaration_orders(self):
        for siblings in (
            'void #f ( ) { : : return } void #g ( ) { : : return }',
            'void #g ( ) { : : return } void #f ( ) { : : return }',
        ):
            result = resolve(f': {siblings} : #f ( ) ; #g ( ) ; ')
            for spelling in ("#f", "#g"):
                symbol, = named(result, spelling)
                self.assertEqual(result.binding_by_name_node[occurrences(result, spelling)[-1].node_id], symbol.symbol_id)

    def test_undeclared_self_sibling_mutual_ancestor_and_deep_calls_fail(self):
        cases = (
            (': : #missing ( ) ; ', '#missing'),
            (': void #f ( ) { : : #f ( ) ; return } : ', '#f'),
            (': void #f ( ) { : : #g ( ) ; return } void #g ( ) { : : return } : ', '#g'),
            (': void #f ( ) { : : #g ( ) ; return } void #g ( ) { : : #f ( ) ; return } : ', '#g'),
            (': void #f ( ) { : void #g ( ) { : : #f ( ) ; return } : return } : ', '#f'),
            (': void #f ( ) { : void #g ( ) { : : return } : return } : #g ( ) ; ', '#g'),
        )
        for text, spelling in cases:
            with self.subTest(text=text):
                self.assert_name_error(text, "NAME-INVISIBLE-FUNCTION", spelling)

    def test_branch_and_all_loop_forms_share_containing_p_environment(self):
        result = resolve(
            '#x : void #f ( ) { : : return } : '
            'if eq ( #x 0 ) then { #x = 1 ; #f ( ) ; } else { print ( #x ) ; } ; '
            'while lesser ( #x 2 ) do { #x = add ( #x 1 ) ; #f ( ) ; } ; '
            'until eq ( #x 3 ) do { #f ( ) ; } ; '
            'do { #f ( ) ; } while larger ( #x 0 ) ; '
            'do { #f ( ) ; } until eq ( #x 0 ) ; '
        )
        self.assertEqual(len(result.scopes), 2)  # Main + declared function only.
        for spelling in ("#x", "#f"):
            symbol, = named(result, spelling)
            self.assertEqual({result.binding_by_name_node[n.node_id] for n in occurrences(result, spelling)}, {symbol.symbol_id})

    def test_assign_arithmetic_print_conditions_and_nested_actuals_bind_variables(self):
        result = resolve(
            '#x #y : num #f ( #p ) { : : return ( #p ) } : '
            '#x = neg ( add ( #y mul ( #f ( #x ) div ( #y 2 ) ) ) ) ; '
            'if and ( eq ( #x #y ) not ( lesser ( #f ( #y ) #x ) ) ) '
            'then { print ( #f ( #x ) ) ; } else { nop ; } ; '
        )
        for spelling in ("#x", "#y", "#p", "#f"):
            symbol, = named(result, spelling)
            self.assertEqual({result.binding_by_name_node[n.node_id] for n in occurrences(result, spelling)}, {symbol.symbol_id})

    def test_return_term_uses_body_locals_parameters_ancestors_and_child_calls(self):
        result = resolve(
            '#global : num #f ( #p ) { #local : num #g ( #a ) { : : return ( #a ) } '
            ': return ( add ( #g ( #local ) add ( #p #global ) ) ) } : #global = #f ( 1 ) ; '
        )
        for spelling in ('#global', '#p', '#local', '#g', '#a'):
            symbol, = named(result, spelling)
            for node in occurrences(result, spelling):
                self.assertEqual(result.binding_by_name_node[node.node_id], symbol.symbol_id)
        function, = named(result, '#f')
        self.assertEqual([result.symbols[i].original_name for i in function.parameter_ids], ['#p'])
        return_use = occurrences(result, '#local')[-1]
        self.assertEqual(result.scope_by_node[return_use.node_id], function.body_scope_id)

    def test_invalid_return_variable_and_call_reject_even_in_uncalled_body(self):
        self.assert_name_error(': num #f ( ) { : : return ( #missing ) } : ',
                               "NAME-UNDECLARED-VARIABLE", "#missing")
        self.assert_name_error(': num #f ( ) { : : return ( #f ( ) ) } : ',
                               "NAME-INVISIBLE-FUNCTION", "#f")

    def test_undeclared_variables_fail_in_every_name_bearing_context(self):
        for algorithm in ('#x = 1 ;', 'print ( #x ) ;',
                          'if eq ( #x 0 ) then { } else { } ;',
                          '#known = neg ( #x ) ;', '#f ( add ( 1 #x ) ) ;'):
            with self.subTest(algorithm=algorithm):
                self.assert_name_error(
                    '#known : void #f ( #a ) { : : return } : ' + algorithm + ' ',
                    "NAME-UNDECLARED-VARIABLE", "#x",
                )

    def test_cross_kind_spelling_collision_is_provisional_separate_namespace_policy(self):
        result = resolve('#f : num #f ( ) { : : return ( #f ) } : #f = #f ( ) ; ')
        variable, = named(result, '#f', SymbolKind.VARIABLE)
        function, = named(result, '#f', SymbolKind.FUNCTION)
        self.assertNotEqual(variable.internal_name, function.internal_name)
        self.assertEqual([result.binding_by_name_node[n.node_id] for n in occurrences(result, '#f')],
                         [variable.symbol_id, function.symbol_id, variable.symbol_id,
                          variable.symbol_id, function.symbol_id])

    def test_variable_is_not_callable_and_function_is_not_variable(self):
        self.assert_name_error('#f : : #f ( ) ; ', 'NAME-INVISIBLE-FUNCTION', '#f')
        self.assert_name_error(': void #f ( ) { : : return } : print ( #f ) ; ',
                               'NAME-UNDECLARED-VARIABLE', '#f')

    def test_name_pass_leaves_arity_numeric_policy_and_call_types_for_later_passes(self):
        result = resolve(': void #f ( #a ) { : : return } : #f ( ) ; #f ( 1 2 ) ; ')
        self.assertIsInstance(result, ResolvedProgram)
        result = resolve('#x : num #f ( ) { : : return ( 1 ) } : #f ( ) ; #x = mod ( 2 div ( 1 2 ) ) ; ')
        self.assertTrue(all(s.value_type is SemanticType.UNKNOWN for s in result.symbols.values()))

    def test_empty_suffix_user_name_remains_legal(self):
        result = resolve('# : : # = 1 ; ')
        symbol, = named(result, '#')
        self.assertEqual(len(occurrences(result, '#')), 2)
        self.assertEqual(set(result.binding_by_name_node.values()), {symbol.symbol_id})

    def test_parameters_preserve_order_and_have_the_body_scope(self):
        result = resolve(': void #f ( #z #a #m ) { : : return } : ')
        function, = named(result, '#f')
        self.assertEqual([result.symbols[i].original_name for i in function.parameter_ids], ['#z', '#a', '#m'])
        self.assertEqual(result.scope_by_node[function.declaration_node_id], function.scope_id)
        for parameter_id in function.parameter_ids:
            parameter = result.symbols[parameter_id]
            self.assertEqual(parameter.scope_id, function.body_scope_id)
            self.assertEqual(result.scope_by_node[parameter.declaration_node_id], parameter.scope_id)

    def test_source_diagnostic_points_to_the_specific_repeated_occurrence(self):
        text = '#x :\r\nvoid #f ( #a ) {\r\n#a : : return } :\r\n'
        error = self.assert_name_error(text, 'NAME-PARAMETER-MASK', '#a')
        self.assertEqual((error.span.line, error.span.column), (3, 1))
        self.assertEqual((error.related_span.line, error.related_span.column), (2, 11))
        self.assertIn('names.spl:3:1: name[NAME-PARAMETER-MASK]', error.render())

    def test_xml_only_diagnostic_uses_node_and_path_without_fake_source_line(self):
        tree, _ = parsed(': : print ( #x ) ; ')
        with self.assertRaises(NameAnalysisError) as raised:
            resolve_names(tree, path=Path('import.xml'))
        error = raised.exception
        self.assertIsNone(error.span)
        self.assertIn(f'import.xml:node[{error.node_id}]', error.render())
        self.assertNotIn(':1:1', error.render())

    def test_success_and_failure_do_not_print_from_library(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            resolve('#x : : #x = 1 ; ')
            with self.assertRaises(NameAnalysisError):
                resolve(': : #x = 1 ; ')
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), '')

    def test_failed_compilation_does_not_change_next_compilation_ids(self):
        first = resolve('#x : : #x = 1 ; ')
        with self.assertRaises(NameAnalysisError):
            resolve('#y : : #missing = 1 ; ')
        second = resolve('#x : : #x = 1 ; ')
        self.assertEqual(first.symbols, second.symbols)
        self.assertEqual(first.binding_by_name_node, second.binding_by_name_node)

    def test_invalid_graph_root_and_orphan_name_context_fail_as_tree_errors(self):
        for make_tree in ('empty', 'root_only', 'name_under_root'):
            with self.subTest(make_tree=make_tree):
                tree = SyntaxTree()
                if make_tree != 'empty':
                    root = tree.add_root('SPL_PROG')
                    if make_tree == 'name_under_root':
                        tree.add_leaf('#x', root.node_id)
                with self.assertRaises(FoundationError):
                    resolve_names(tree)
        tree, _ = parsed(': : print ( 1 ) ; ')
        number = next(n for n in tree.iter_nodes() if n.kind is NodeKind.LEAF and n.contents == '1')
        # Corrupt only the production shape: graph validation still succeeds.
        parent = tree.get_node(number.parent_id)
        parent.contents = 'OUTP'
        number.contents = '#x'
        with self.assertRaises(FoundationError) as raised:
            resolve_names(tree)
        self.assertEqual(raised.exception.code, 'TREE-NAME-CONTEXT')

    def test_bad_source_map_inputs_fail_before_name_resolution(self):
        tree, locations = parsed(': : ')
        with self.assertRaises(ValueError): resolve_names(tree, locations, path=Path('different.spl'))
        with self.assertRaises(ValueError): resolve_names(tree, {})
        with self.assertRaises(ValueError): resolve_names(tree, path='input.spl')
        foreign = SourceMap(PATH, {999: SourceSpan(PATH, 1, 1, 0, 1, 2, 1)})
        with self.assertRaises(FoundationError) as raised:
            resolve_names(tree, foreign)
        self.assertEqual(raised.exception.code, 'MAP-NODE')

    def test_imported_call_requires_a_name_and_valid_input_list(self):
        for corrupt in ('name', 'input'):
            with self.subTest(corrupt=corrupt):
                tree, _ = parsed(': void #f ( ) { : : return } : #f ( ) ; ')
                call = next(n for n in tree.iter_nodes() if n.contents == 'CALL')
                node = tree.get_node(call.child_ids[0 if corrupt == 'name' else 2])
                node.contents = '1' if corrupt == 'name' else 'ALGO'
                with self.assertRaises(FoundationError) as raised:
                    resolve_names(tree)
                self.assertEqual(raised.exception.code, 'TREE-SHAPE')

    def test_deep_function_tree_uses_iterative_analysis(self):
        # Build a parser-shaped tree directly so this tests semantic traversal,
        # independently of the existing recursive parser's depth limit.
        tree = SyntaxTree()
        root = tree.add_root('SPL_PROG')
        p = tree.add_inner('P', root.node_id)
        for depth in range(1100):
            tree.add_inner('V_DECL', p.node_id)
            tree.add_leaf(':', p.node_id)
            declarations = tree.add_inner('F_DECL', p.node_id)
            tree.add_leaf(':', p.node_id)
            algo = tree.add_inner('ALGO', p.node_id)
            if depth == 1099:
                break
            function = tree.add_inner('F_TYPE', declarations.node_id)
            tree.add_inner('F_DECL', declarations.node_id)
            for lexeme in ('void', '#f', '('): tree.add_leaf(lexeme, function.node_id)
            tree.add_inner('V_DECL', function.node_id)
            for lexeme in (')', '{'): tree.add_leaf(lexeme, function.node_id)
            p = tree.add_inner('P', function.node_id)
            for lexeme in ('return', '}'): tree.add_leaf(lexeme, function.node_id)
            instruction = tree.add_inner('INSTR', algo.node_id)
            tree.add_leaf(';', algo.node_id)
            tree.add_inner('ALGO', algo.node_id)
            call = tree.add_inner('CALL', instruction.node_id)
            tree.add_leaf('#f', call.node_id)
            tree.add_leaf('(', call.node_id)
            tree.add_inner('INPUT', call.node_id)
            tree.add_leaf(')', call.node_id)
        result = resolve_names(tree)
        self.assertEqual(len(result.scopes), 1100)
        order = build_call_hierarchy(result).bottom_up_function_ids
        self.assertEqual(len(order), 1099)
        self.assertEqual(order, tuple(reversed(range(1, 1100))))


class CallHierarchyTests(unittest.TestCase):
    def test_edges_deduplicate_calls_and_order_callees_before_callers(self):
        result = resolve(
            ': void #f ( ) { : void #g ( ) { : : return } '
            'void #unused ( ) { : : return } : #g ( ) ; #g ( ) ; return } '
            ': #f ( ) ; #f ( ) ; '
        )
        f, = named(result, '#f'); g, = named(result, '#g'); unused, = named(result, '#unused')
        hierarchy = build_call_hierarchy(result)
        self.assertEqual(hierarchy.callees_by_caller,
                         {None: (f.symbol_id,), f.symbol_id: (g.symbol_id,), g.symbol_id: (), unused.symbol_id: ()})
        self.assertLess(hierarchy.bottom_up_function_ids.index(g.symbol_id), hierarchy.bottom_up_function_ids.index(f.symbol_id))
        self.assertEqual(set(hierarchy.bottom_up_function_ids), {f.symbol_id, g.symbol_id, unused.symbol_id})
        with self.assertRaises(TypeError): hierarchy.callees_by_caller[None] = ()

    def test_guard_rejects_self_cycle_in_modified_binding_snapshot(self):
        result = resolve(': void #f ( ) { : void #f ( ) { : : return } : #f ( ) ; return } : ')
        parent, child = named(result, '#f')
        call_name = occurrences(result, '#f')[-1]
        bindings = dict(result.binding_by_name_node)
        bindings[call_name.node_id] = parent.symbol_id
        forged = replace(result, binding_by_name_node=bindings)
        with self.assertRaises(NameAnalysisError) as raised:
            build_call_hierarchy(forged)
        self.assertEqual(raised.exception.code, 'NAME-RECURSION')

    def test_guard_rejects_indirect_cycle_in_modified_binding_snapshot(self):
        result = resolve(
            ': void #f ( ) { : void #g ( ) { : : return } : #g ( ) ; return } '
            'void #g ( ) { : void #f ( ) { : : return } : #f ( ) ; return } : '
        )
        root_f = next(s for s in named(result, '#f') if s.scope_id == 1)
        root_g = next(s for s in named(result, '#g') if s.scope_id == 1)
        bindings = dict(result.binding_by_name_node)
        for node in result.tree.iter_nodes():
            if node.kind is NodeKind.LEAF and node.contents in {'#f', '#g'}:
                parent = result.tree.get_node(node.parent_id)
                if parent.contents == 'CALL':
                    bindings[node.node_id] = root_f.symbol_id if node.contents == '#f' else root_g.symbol_id
        with self.assertRaises(NameAnalysisError) as raised:
            build_call_hierarchy(replace(result, binding_by_name_node=bindings))
        self.assertEqual(raised.exception.code, 'NAME-RECURSION')

    def test_guard_rejects_noncyclic_sideways_rebinding(self):
        result = resolve(
            ': void #f ( ) { : void #g ( ) { : : return } : #g ( ) ; return } '
            'void #g ( ) { : : return } : '
        )
        root_g = next(s for s in named(result, '#g') if s.scope_id == 1)
        call_name = occurrences(result, '#g')[1]
        forged = replace(result, binding_by_name_node={**result.binding_by_name_node, call_name.node_id: root_g.symbol_id})
        with self.assertRaises(NameAnalysisError) as raised:
            build_call_hierarchy(forged)
        self.assertEqual(raised.exception.code, 'NAME-INVISIBLE-FUNCTION')


if __name__ == '__main__':
    unittest.main()
