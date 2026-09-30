from pathlib import Path
import unittest

from spl_frontend.diagnostics import ExitCode, FrontendError
from spl_frontend.parser import parse
from spl_frontend.token_stream import TokenStream
from spl_frontend.tokens import Token, TokenType
from spl_frontend.tree import NodeKind, SyntaxTree

KEYWORDS = {member.value: member for member in TokenType}


def tok(lexeme, i):
    if lexeme.startswith('#'):
        typ = TokenType.USER_NAME
    elif lexeme.startswith('"'):
        typ = TokenType.STRING
    elif lexeme and (
        lexeme[0].isdigit()
        or (lexeme[0] == '-' and len(lexeme) > 1 and lexeme[1].isdigit())
    ):
        typ = TokenType.NUM
    else:
        typ = KEYWORDS[lexeme]
    return Token(typ, lexeme, 1, i + 1, i)


def tokens(*lexemes):
    result = [tok(lexeme, i) for i, lexeme in enumerate(lexemes)]
    result.append(Token(TokenType.EOF, '', 1, len(lexemes) + 1, len(lexemes)))
    return result


def parse_program(*lexemes):
    tree = SyntaxTree()
    result = parse(tokens(*lexemes), tree)
    if result is not tree:
        raise AssertionError('parse() must return the supplied SyntaxTree')
    return tree


def inner_contents(tree):
    return [
        node.contents
        for node in tree.iter_nodes()
        if node.kind in (NodeKind.ROOT, NodeKind.INNER)
    ]


def leaves(tree):
    return [node.contents for node in tree.iter_nodes() if node.kind is NodeKind.LEAF]


def assert_valid(test_case, tree, source_lexemes):
    tree.validate()
    test_case.assertIsNotNone(tree.root)
    test_case.assertEqual(tree.root.contents, 'SPL_PROG')
    test_case.assertNotIn('$', leaves(tree))
    test_case.assertEqual(leaves(tree), list(source_lexemes))
    test_case.assertTrue(
        all(node.node_id == i for i, node in enumerate(tree.iter_nodes(), 1))
    )


class ParserTests(unittest.TestCase):
    def test_smallest_valid_program_and_all_nullable_sections(self):
        source = (':', ':')
        tree = parse_program(*source)
        assert_valid(self, tree, source)
        self.assertEqual(
            inner_contents(tree),
            ['SPL_PROG', 'P', 'V_DECL', 'F_DECL', 'ALGO'],
        )

    def test_variable_declaration_chain_and_function_declaration_chain(self):
        source = (
            '#a', '#b', ':', 'void', '#f', '(', '#p', '#q', ')', '{', ':', ':',
            'return', '}', 'num', '#g', '(', ')', '{', ':', ':', 'return', '(',
            '1', ')', '}', ':',
        )
        tree = parse_program(*source)
        assert_valid(self, tree, source)
        self.assertGreaterEqual(inner_contents(tree).count('V_DECL'), 4)
        self.assertGreaterEqual(inner_contents(tree).count('F_DECL'), 3)
        self.assertEqual(inner_contents(tree).count('F_TYPE'), 2)

    def test_void_and_numeric_functions_and_nested_p(self):
        source = (
            '#x', ':', 'void', '#f', '(', '#p', ')', '{', '#local', ':', ':',
            'nop', ';', 'return', '}', 'num', '#g', '(', '#a', ')', '{', '#nested',
            ':', 'void', '#h', '(', ')', '{', ':', ':', 'return', '}', ':',
            'return', '(', '#nested', ')', '}', ':', 'nop', ';',
        )
        tree = parse_program(*source)
        assert_valid(self, tree, source)

    def test_every_instruction_alternative(self):
        instructions = [
            ('print', '"hello"'),
            ('print', '(', '1', ')'),
            ('nop',),
            ('comment', '"note"'),
            ('#x', '=', '1'),
            ('#f', '(', ')'),
            ('if', 'eq', '(', '1', '2', ')', 'then', '{', '}', 'else', '{', '}'),
            ('while', 'eq', '(', '1', '2', ')', 'do', '{', '}'),
            ('do', '{', '}', 'until', 'eq', '(', '1', '2', ')'),
        ]
        for instruction in instructions:
            with self.subTest(instruction=instruction):
                source = (':', ':', *instruction, ';')
                tree = parse_program(*source)
                assert_valid(self, tree, source)

    def test_every_term_alternative(self):
        terms = [
            ('#x',),
            ('1',),
            ('#f', '(', ')'),
            ('mod', '(', '1', '2', ')'),
            ('add', '(', '1', '2', ')'),
            ('sub', '(', '1', '2', ')'),
            ('mul', '(', '1', '2', ')'),
            ('div', '(', '1', '2', ')'),
            ('neg', '(', '1', ')'),
        ]
        for term in terms:
            with self.subTest(term=term):
                source = (':', ':', '#x', '=', *term, ';')
                tree = parse_program(*source)
                assert_valid(self, tree, source)

    def test_every_arithmetic_operator(self):
        operators = ['mod', 'add', 'sub', 'mul', 'div']
        for operator in operators:
            with self.subTest(operator=operator):
                source = (
                    ':', ':', '#x', '=', operator, '(', '#a', 'neg', '(', '2', ')', ')', ';'
                )
                tree = parse_program(*source)
                assert_valid(self, tree, source)

    def test_calls_empty_one_and_multiple_inputs(self):
        source = (
            ':', ':', '#f', '(', ')', ';', '#g', '(', '1', ')', ';', '#h', '(',
            '#a', '2', 'add', '(', '3', '4', ')', ')', ';',
        )
        tree = parse_program(*source)
        assert_valid(self, tree, source)
        self.assertEqual(leaves(tree).count('('), 4)

    def test_every_boolean_and_comparison_operator(self):
        booleans = [
            ('not', '(', 'eq', '(', '1', '2', ')', ')'),
            ('and', '(', 'eq', '(', '1', '2', ')', 'larger', '(', '3', '2', ')', ')'),
            ('or', '(', 'lesser', '(', '1', '2', ')', 'eq', '(', '3', '3', ')', ')'),
            ('eq', '(', '1', '2', ')'),
            ('larger', '(', '1', '2', ')'),
            ('lesser', '(', '1', '2', ')'),
        ]
        for boolean in booleans:
            with self.subTest(boolean=boolean):
                source = (':', ':', 'if', *boolean, 'then', '{', '}', 'else', '{', '}', ';')
                tree = parse_program(*source)
                assert_valid(self, tree, source)

    def test_both_loop_forms(self):
        sources = [
            (':', ':', 'while', 'eq', '(', '1', '2', ')', 'do', '{', '}', ';'),
            (':', ':', 'until', 'lesser', '(', '1', '2', ')', 'do', '{', 'nop', ';', '}', ';'),
            (':', ':', 'do', '{', 'nop', ';', '}', 'while', 'larger', '(', '2', '1', ')', ';'),
        ]
        for source in sources:
            with self.subTest(source=source):
                tree = parse_program(*source)
                assert_valid(self, tree, source)

    def test_deep_nesting_and_multiple_sequential_instructions(self):
        boolean = ('eq', '(', '1', '2', ')')
        for _ in range(40):
            boolean = ('not', '(', *boolean, ')')
        source = (
            ':', ':', 'print', '"x"', ';', '#x', '=', 'add', '(', '1', 'mul', '(',
            '2', '3', ')', ')', ';', 'if', *boolean, 'then', '{', 'nop', ';', '}',
            'else', '{', 'comment', '"y"', ';', '}', ';',
        )
        tree = parse_program(*source)
        assert_valid(self, tree, source)

    def test_user_name_lookahead_assignment_vs_call(self):
        assignment = parse_program(':', ':', '#x', '=', '1', ';')
        call = parse_program(':', ':', '#x', '(', '1', ')', ';')
        self.assertIn('ASSIGN', inner_contents(assignment))
        self.assertIn('CALL', inner_contents(call))

    def test_user_name_lookahead_term_vs_call(self):
        name_term = parse_program(':', ':', '#x', '=', '#y', ';')
        call_term = parse_program(':', ':', '#x', '=', '#y', '(', ')', ';')
        self.assertNotIn('CALL', inner_contents(name_term))
        self.assertIn('CALL', inner_contents(call_term))

    def test_missing_delimiters_or_required_keywords(self):
        sources = [
            (':', '#x'),
            (':', ':', 'print', '"x"'),
            (':', ':', '{'),
            (':', ':', 'print', '(', '1', ';'),
            (':', ':', '#x', '=', 'add', '(', '1', ')', ';'),
            (':', ':', '#x', '(', '1', ';'),
            (':', ':', 'if', 'eq', '(', '1', '2', ')', '{', '}', 'else', '{', '}', ';'),
            (':', ':', 'if', 'eq', '(', '1', '2', ')', 'then', '{', '}', '{', '}', ';'),
            (':', ':', 'while', 'eq', '(', '1', '2', ')', '{', '}', ';'),
        ]
        for source in sources:
            with self.subTest(source=source), self.assertRaises(FrontendError) as exc_info:
                parse_program(*source)
            error = exc_info.exception
            self.assertIs(error.exit_code, ExitCode.SYNTAX_ERROR)
            self.assertEqual(error.diagnostic.phase.value, 'syntax')
            self.assertTrue(error.diagnostic.code.startswith('SYN-'))
            self.assertIn('unexpected token', error.diagnostic.message)
            self.assertIn('expected', error.diagnostic.message)
            self.assertGreaterEqual(error.diagnostic.line, 1)
            self.assertGreaterEqual(error.diagnostic.column, 1)
            self.assertTrue(error.diagnostic.hint)

    def test_name_following_neither_assignment_nor_call_has_focused_error(self):
        with self.assertRaises(FrontendError) as exc_info:
            parse_program(':', ':', '#x', ';')
        diagnostic = exc_info.exception.diagnostic
        self.assertEqual(diagnostic.code, 'SYN-NAME-FOLLOW')
        self.assertIn("'='", diagnostic.message)
        self.assertIn("'('", diagnostic.message)
        self.assertIsNotNone(diagnostic.hint)
        self.assertTrue(diagnostic.hint)

    def test_invalid_term_name_lookahead_is_not_speculatively_parsed_as_call(self):
        with self.assertRaises(FrontendError) as exc_info:
            parse_program(':', ':', '#x', '=', '#y', '=', '1', ';')
        diagnostic = exc_info.exception.diagnostic
        self.assertEqual(diagnostic.phase.value, 'syntax')
        self.assertEqual(diagnostic.line, 1)
        self.assertGreater(diagnostic.column, 1)

    def test_unexpected_eof_inside_nested_construct(self):
        with self.assertRaises(FrontendError) as exc_info:
            parse_program(':', ':', 'if', 'eq', '(', '1', '2', ')', 'then', '{', 'nop', ';')
        diagnostic = exc_info.exception.diagnostic
        self.assertTrue(diagnostic.message.startswith("unexpected token '<EOF>'"))
        self.assertTrue(diagnostic.hint)

    def test_valid_prefix_followed_by_trailing_input_is_rejected(self):
        with self.assertRaises(FrontendError) as exc_info:
            parse_program(':', ':', 'print', '"x"', ';', 'nop', ';', 'print', '"trailing"')
        diagnostic = exc_info.exception.diagnostic
        self.assertEqual(diagnostic.code, 'SYN-EXPECTED')
        self.assertIn('<EOF>', diagnostic.message)
        self.assertEqual(diagnostic.line, 1)

    def test_invalid_token_in_input_position_is_not_silently_treated_as_empty(self):
        with self.assertRaises(FrontendError):
            parse_program(':', ':', '#f', '(', 'print', ')', ';')

    def test_tree_contains_no_helper_nonterminals_and_no_eof_leaf(self):
        source = (':', ':', 'print', '"x"', ';')
        tree = parse_program(*source)
        grammar_nodes = {
            'SPL_PROG', 'P', 'V_DECL', 'F_DECL', 'F_TYPE', 'ALGO', 'OUTP', 'INSTR',
            'CALL', 'INPUT', 'ASSIGN', 'TERM', 'BRANCH', 'BOOL', 'LOOP', 'COND',
        }
        self.assertLessEqual(set(inner_contents(tree)), grammar_nodes)
        self.assertNotIn('$', leaves(tree))

    def test_token_stream_is_untouched_by_peek_and_consumes_until_eof(self):
        supplied = tokens(':', ':')
        stream = TokenStream(supplied)
        self.assertEqual(stream.position, 0)
        self.assertEqual(stream.peek().lexeme, ':')
        self.assertEqual(stream.position, 0)
        self.assertIs(stream.peek(99).token_type, TokenType.EOF)
        self.assertEqual(stream.position, 0)
        self.assertEqual(stream.consume().lexeme, ':')
        self.assertEqual(stream.consume().lexeme, ':')
        self.assertTrue(stream.at_end())
        self.assertIs(stream.consume().token_type, TokenType.EOF)
        self.assertEqual(stream.position, 2)


if __name__ == '__main__':
    unittest.main()
