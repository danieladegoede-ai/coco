"""Predictive parser for the approved SPL grammar."""
from __future__ import annotations
from collections.abc import Sequence
from pathlib import Path
from spl_frontend.cli_contract import DEFAULT_INPUT_PATH
from spl_frontend.diagnostics import Diagnostic, DiagnosticPhase, ExitCode, FrontendError
from spl_frontend.token_stream import TokenStream
from spl_frontend.tokens import Token, TokenType
from spl_frontend.tree import SyntaxTree

_TERM_START=(TokenType.USER_NAME,TokenType.NUM,TokenType.MOD,TokenType.ADD,TokenType.SUB,TokenType.MUL,TokenType.DIV,TokenType.NEG)
_BOOL_START=(TokenType.NOT,TokenType.AND,TokenType.OR,TokenType.EQ,TokenType.LARGER,TokenType.LESSER)
_INSTR_START=(TokenType.PRINT,TokenType.NOP,TokenType.COMMENT,TokenType.USER_NAME,TokenType.IF,TokenType.WHILE,TokenType.UNTIL,TokenType.DO)
_ARITH_BINARY=(TokenType.MOD,TokenType.ADD,TokenType.SUB,TokenType.MUL,TokenType.DIV)
_ALGO_FOLLOW=(TokenType.EOF,TokenType.RETURN,TokenType.RBRACE)

class _Parser:
    def __init__(self, stream:TokenStream, tree:SyntaxTree, path:Path=DEFAULT_INPUT_PATH):
        self.stream=stream; self.tree=tree; self.path=path
    def peek(self,distance:int=0)->Token: return self.stream.peek(distance)
    def match(self,*types:TokenType)->bool: return self.peek().token_type in types
    def _display(self, token_or_type:Token|TokenType)->str:
        if isinstance(token_or_type,Token):
            return token_or_type.lexeme if token_or_type.lexeme else '<EOF>'
        if token_or_type is TokenType.EOF: return '<EOF>'
        if token_or_type in (TokenType.USER_NAME,TokenType.NUM,TokenType.STRING): return token_or_type.value
        return repr(token_or_type.value)
    def _expected(self, types:Sequence[TokenType])->str:
        vals=[self._display(t) for t in types]
        if len(vals)==1: return vals[0]
        return '{'+', '.join(vals)+'}'
    def _default_hint(self, expected:Sequence[TokenType], token:Token)->str:
        if token.token_type is TokenType.EOF: return 'the input ended before the required grammar element was complete.'
        if len(expected)==1:
            hints={TokenType.COLON:"use ':' to separate variable, function and algorithm sections.", TokenType.SEMICOLON:"every instruction in ALGO must end with ';'.", TokenType.LPAREN:"this construct requires an opening '('.", TokenType.RPAREN:"this construct must close with ')'.", TokenType.LBRACE:"this block requires an opening '{'.", TokenType.RBRACE:"this block must close with '}'.", TokenType.RETURN:"a function body must end with the required 'return' keyword.", TokenType.THEN:"an if condition must be followed by 'then'.", TokenType.ELSE:"a branch must contain an 'else' block.", TokenType.DO:"a loop condition must be followed by 'do'."}
            if expected[0] in hints: return hints[expected[0]]
        return 'check the tokens immediately before and after this location against the SPL grammar.'
    def _error(self, expected:Sequence[TokenType], token:Token|None=None, hint:str|None=None, code:str='SYN-EXPECTED')->None:
        found=self.peek() if token is None else token
        expected_tuple=tuple(expected)
        diagnostic=Diagnostic(DiagnosticPhase.SYNTAX,code,f"unexpected token {self._display(found)!r}; expected {self._expected(expected_tuple)}",self.path,found.line,found.column,hint or self._default_hint(expected_tuple,found))
        raise FrontendError(ExitCode.SYNTAX_ERROR,diagnostic)
    def expect(self,parent_id:int,*expected:TokenType,hint:str|None=None)->Token:
        token=self.peek()
        if token.token_type not in expected: self._error(expected,token,hint)
        token=self.stream.consume()
        if token.token_type is not TokenType.EOF: self.tree.add_leaf(token.lexeme,parent_id)
        return token
    def parse_spl_prog(self)->None:
        root=self.tree.add_root('SPL_PROG')
        self.parse_p(root.node_id)
        self.expect(root.node_id,TokenType.EOF,hint='the complete SPL program must be followed only by internal EOF.')
    def parse_p(self,parent_id:int)->None:
        node=self.tree.add_inner('P',parent_id)
        self.parse_v_decl(node.node_id)
        self.expect(node.node_id,TokenType.COLON)
        self.parse_f_decl(node.node_id)
        self.expect(node.node_id,TokenType.COLON)
        self.parse_algo(node.node_id)
    def parse_v_decl(self,parent_id:int)->None:
        node=self.tree.add_inner('V_DECL',parent_id)
        current=node
        while self.match(TokenType.USER_NAME):
            self.expect(current.node_id,TokenType.USER_NAME)
            current=self.tree.add_inner('V_DECL',current.node_id)
        if not self.match(TokenType.COLON,TokenType.RPAREN): self._error((TokenType.USER_NAME,TokenType.COLON,TokenType.RPAREN))
    def parse_f_decl(self,parent_id:int)->None:
        node=self.tree.add_inner('F_DECL',parent_id)
        current=node
        while self.match(TokenType.VOID,TokenType.NUM_TYPE):
            self.parse_f_type(current.node_id)
            current=self.tree.add_inner('F_DECL',current.node_id)
        if not self.match(TokenType.COLON): self._error((TokenType.VOID,TokenType.NUM_TYPE,TokenType.COLON))
    def parse_f_type(self,parent_id:int)->None:
        node=self.tree.add_inner('F_TYPE',parent_id)
        if self.match(TokenType.VOID):
            self.expect(node.node_id,TokenType.VOID)
            self.expect(node.node_id,TokenType.USER_NAME)
            self.expect(node.node_id,TokenType.LPAREN)
            self.parse_v_decl(node.node_id)
            self.expect(node.node_id,TokenType.RPAREN)
            self.expect(node.node_id,TokenType.LBRACE)
            self.parse_p(node.node_id)
            self.expect(node.node_id,TokenType.RETURN)
            self.expect(node.node_id,TokenType.RBRACE)
            return
        if self.match(TokenType.NUM_TYPE):
            self.expect(node.node_id,TokenType.NUM_TYPE)
            self.expect(node.node_id,TokenType.USER_NAME)
            self.expect(node.node_id,TokenType.LPAREN)
            self.parse_v_decl(node.node_id)
            self.expect(node.node_id,TokenType.RPAREN)
            self.expect(node.node_id,TokenType.LBRACE)
            self.parse_p(node.node_id)
            self.expect(node.node_id,TokenType.RETURN)
            self.expect(node.node_id,TokenType.LPAREN)
            self.parse_term(node.node_id)
            self.expect(node.node_id,TokenType.RPAREN)
            self.expect(node.node_id,TokenType.RBRACE)
            return
        self._error((TokenType.VOID,TokenType.NUM_TYPE))
    def parse_algo(self,parent_id:int)->None:
        node=self.tree.add_inner('ALGO',parent_id)
        current=node
        while self.match(*_INSTR_START):
            self.parse_instr(current.node_id)
            self.expect(current.node_id,TokenType.SEMICOLON)
            current=self.tree.add_inner('ALGO',current.node_id)
        if not self.match(*_ALGO_FOLLOW): self._error((*_INSTR_START,*_ALGO_FOLLOW))
    def parse_outp(self,parent_id:int)->None:
        node=self.tree.add_inner('OUTP',parent_id)
        if self.match(TokenType.LPAREN):
            self.expect(node.node_id,TokenType.LPAREN)
            self.parse_term(node.node_id)
            self.expect(node.node_id,TokenType.RPAREN)
            return
        if self.match(TokenType.STRING): self.expect(node.node_id,TokenType.STRING); return
        self._error((TokenType.LPAREN,TokenType.STRING))
    def parse_instr(self,parent_id:int)->None:
        node=self.tree.add_inner('INSTR',parent_id)
        if self.match(TokenType.PRINT):
            self.expect(node.node_id,TokenType.PRINT); self.parse_outp(node.node_id); return
        if self.match(TokenType.NOP): self.expect(node.node_id,TokenType.NOP); return
        if self.match(TokenType.COMMENT):
            self.expect(node.node_id,TokenType.COMMENT); self.expect(node.node_id,TokenType.STRING); return
        if self.match(TokenType.USER_NAME):
            following=self.peek(1).token_type
            if following is TokenType.ASSIGN: self.parse_assign(node.node_id); return
            if following is TokenType.LPAREN: self.parse_call(node.node_id); return
            self._error((TokenType.ASSIGN,TokenType.LPAREN),self.peek(1),"after a user-defined name in instruction position, use '=' for assignment or '(' for a call.",'SYN-NAME-FOLLOW')
        if self.match(TokenType.IF): self.parse_branch(node.node_id); return
        if self.match(TokenType.WHILE,TokenType.UNTIL,TokenType.DO): self.parse_loop(node.node_id); return
        self._error(_INSTR_START)
    def parse_call(self,parent_id:int)->None:
        node=self.tree.add_inner('CALL',parent_id)
        self.expect(node.node_id,TokenType.USER_NAME)
        self.expect(node.node_id,TokenType.LPAREN)
        self.parse_input(node.node_id)
        self.expect(node.node_id,TokenType.RPAREN)
    def parse_input(self,parent_id:int)->None:
        node=self.tree.add_inner('INPUT',parent_id)
        current=node
        if self.match(TokenType.RPAREN): return
        if not self.match(*_TERM_START): self._error((*_TERM_START,TokenType.RPAREN))
        while self.match(*_TERM_START):
            self.parse_term(current.node_id)
            current=self.tree.add_inner('INPUT',current.node_id)
        if not self.match(TokenType.RPAREN): self._error((*_TERM_START,TokenType.RPAREN))
    def parse_assign(self,parent_id:int)->None:
        node=self.tree.add_inner('ASSIGN',parent_id)
        self.expect(node.node_id,TokenType.USER_NAME)
        self.expect(node.node_id,TokenType.ASSIGN)
        self.parse_term(node.node_id)
    def parse_term(self,parent_id:int)->None:
        node=self.tree.add_inner('TERM',parent_id)
        if self.match(TokenType.USER_NAME):
            if self.peek(1).token_type is TokenType.LPAREN: self.parse_call(node.node_id)
            else: self.expect(node.node_id,TokenType.USER_NAME)
            return
        if self.match(TokenType.NUM): self.expect(node.node_id,TokenType.NUM); return
        if self.match(*_ARITH_BINARY):
            operator=self.peek().token_type
            self.expect(node.node_id,operator)
            self.expect(node.node_id,TokenType.LPAREN)
            self.parse_term(node.node_id); self.parse_term(node.node_id)
            self.expect(node.node_id,TokenType.RPAREN); return
        if self.match(TokenType.NEG):
            self.expect(node.node_id,TokenType.NEG); self.expect(node.node_id,TokenType.LPAREN); self.parse_term(node.node_id); self.expect(node.node_id,TokenType.RPAREN); return
        self._error(_TERM_START)
    def parse_branch(self,parent_id:int)->None:
        node=self.tree.add_inner('BRANCH',parent_id)
        self.expect(node.node_id,TokenType.IF)
        self.parse_bool(node.node_id)
        self.expect(node.node_id,TokenType.THEN)
        self.expect(node.node_id,TokenType.LBRACE)
        self.parse_algo(node.node_id)
        self.expect(node.node_id,TokenType.RBRACE)
        self.expect(node.node_id,TokenType.ELSE)
        self.expect(node.node_id,TokenType.LBRACE)
        self.parse_algo(node.node_id)
        self.expect(node.node_id,TokenType.RBRACE)
    def parse_bool(self,parent_id:int)->None:
        node=self.tree.add_inner('BOOL',parent_id)
        if self.match(TokenType.NOT):
            self.expect(node.node_id,TokenType.NOT); self.expect(node.node_id,TokenType.LPAREN); self.parse_bool(node.node_id); self.expect(node.node_id,TokenType.RPAREN); return
        if self.match(TokenType.AND,TokenType.OR):
            op=self.peek().token_type; self.expect(node.node_id,op); self.expect(node.node_id,TokenType.LPAREN); self.parse_bool(node.node_id); self.parse_bool(node.node_id); self.expect(node.node_id,TokenType.RPAREN); return
        if self.match(TokenType.EQ,TokenType.LARGER,TokenType.LESSER):
            op=self.peek().token_type; self.expect(node.node_id,op); self.expect(node.node_id,TokenType.LPAREN); self.parse_term(node.node_id); self.parse_term(node.node_id); self.expect(node.node_id,TokenType.RPAREN); return
        self._error(_BOOL_START)
    def parse_loop(self,parent_id:int)->None:
        node=self.tree.add_inner('LOOP',parent_id)
        if self.match(TokenType.WHILE,TokenType.UNTIL):
            self.parse_cond(node.node_id); self.parse_bool(node.node_id); self.expect(node.node_id,TokenType.DO); self.expect(node.node_id,TokenType.LBRACE); self.parse_algo(node.node_id); self.expect(node.node_id,TokenType.RBRACE); return
        if self.match(TokenType.DO):
            self.expect(node.node_id,TokenType.DO); self.expect(node.node_id,TokenType.LBRACE); self.parse_algo(node.node_id); self.expect(node.node_id,TokenType.RBRACE); self.parse_cond(node.node_id); self.parse_bool(node.node_id); return
        self._error((TokenType.WHILE,TokenType.UNTIL,TokenType.DO))
    def parse_cond(self,parent_id:int)->None:
        node=self.tree.add_inner('COND',parent_id)
        self.expect(node.node_id,TokenType.WHILE,TokenType.UNTIL)

def parse(
    tokens: Sequence[Token],
    tree: SyntaxTree,
    path: Path = DEFAULT_INPUT_PATH,
) -> SyntaxTree:
    parser = _Parser(TokenStream(tokens), tree, path)
    parser.parse_spl_prog()
    tree.validate()
    return tree