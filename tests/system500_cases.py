"""500 deterministic, independently expected complete-system regression cases.

Expectations below use small integer algebra, Boolean truth tables and explicit
state transitions, never generated C++, compiler IR or the SPL model evaluator.
The inventory records source hashes without committing private course material.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from collections import Counter


@dataclass(frozen=True)
class SystemCase:
    case_id: str
    family: str
    scenario: str
    source: str
    stdout: str = ""
    status: int = 0
    code: str = ""
    requirements: tuple[str, ...] = ()
    profile: str = "execute"
    basis: str = "explicit state/output calculation"

    def inventory(self) -> dict:
        return {"id": self.case_id, "family": self.family, "scenario": self.scenario,
                "source_sha256": hashlib.sha256(self.source.encode()).hexdigest(),
                "source_bytes": len(self.source.encode()), "expected_status": self.status,
                "expected_code": self.code, "expected_stdout": self.stdout,
                "requirements": list(self.requirements), "profile": self.profile,
                "expectation_basis": self.basis}


def _wrap(source: str, depth: int) -> str:
    # Semantic checks must visit even never-called bodies at each nesting level.
    for level in range(depth):
        source = f': void #shell{level} ( ) {{ {source} return }} : '
    return source


def build_cases() -> tuple[SystemCase, ...]:
    cases: list[SystemCase] = []

    def add(family: str, scenario: str, source: str, stdout: str = "", *,
            status: int = 0, code: str = "", req: str = "", profile: str = "execute",
            basis: str = "explicit state/output calculation") -> None:
        cases.append(SystemCase(f"SYS{len(cases)+1:04d}", family, scenario, source,
                                stdout, status, code, tuple(req.split()), profile, basis))

    # Ten different expression shapes, with signed/zero/boundary operands.
    for i in range(5):
        a, b = i - 2, i + 3
        expressions = [
            (f'add ( {a} {b} )', a+b, 'addition'),
            (f'sub ( {a} {b} )', a-b, 'subtraction'),
            (f'mul ( {a} {b} )', a*b, 'multiplication'),
            (f'neg ( {a} )', -a, 'negation'),
            (f'mod ( {-17-i} {b} )', -((17+i) % b), 'negative-remainder'),
            (f'add ( mul ( {a} {b} ) neg ( {b} ) )', a*b-b, 'nested-expression'),
            (f'sub ( {a} neg ( {b} ) )', a+b, 'subtract-negative'),
            (f'mul ( add ( {a} {b} ) sub ( {a} {b} ) )', (a+b)*(a-b), 'both-operands-nested'),
            (f'mod ( {17+i} {-b} )', (17+i) % b, 'negative-divisor'),
            (f'neg ( neg ( add ( {a} {b} ) ) )', a+b, 'double-negation'),
        ]
        for expression, value, label in expressions:
            add('arithmetic', f'{label}-{i}',
                f'#x : : #x = {a} ; #x = add ( #x {expression} ) ; '
                'comment "calculation.!" ; nop ; print "v:" ; print ( #x ) ; print "!" ; ',
                f'v:{a+value}!', req='T01 T02 T05 T06 T08 T09 G01 G02 G03 G04 G05 G06',
                basis=f'x starts at {a}; RHS adds independently calculated {value}')

    # All truth-table inputs plus comparisons, nested composition and branch arms.
    for i in range(5):
        a = i - 2
        conditions = [
            (f'eq ( {a} {a} )', True), (f'lesser ( {a} {a} )', False),
        ]
        for op in ('and', 'or'):
            for left, right in ((False,False),(False,True),(True,False),(True,True)):
                l=f'eq ( {a} {a if left else a+1} )'
                r=f'larger ( {a+1 if right else a} {a} )'
                conditions.append((f'not ( {op} ( {l} {r} ) )',
                                   not ((left and right) if op=='and' else (left or right))))
        for j, (condition, truth) in enumerate(conditions):
            add('booleans', f'truth-{i}-{j}',
                f'#x : : #x = {a} ; if {condition} then {{ #x = add ( #x 10 ) ; }} '
                'else { #x = sub ( #x 10 ) ; } ; print ( #x ) ; ',
                str(a+(10 if truth else -10)), req='T07 G07 G08 G10',
                basis=f'Boolean truth table yields {truth}; selected arm changes x by ten')

    for n in range(5):
        for kind in range(10):
            post = kind % 4 >= 2
            until = kind % 4 in (1,3)
            body = '#x = add ( #x 1 ) ; '
            if kind >= 4:
                body += 'if eq ( mod ( #x 2 ) 0 ) then { print "e" ; } else { print "o" ; } ; '
            if kind >= 8:
                body += '#y = 0 ; while lesser ( #y 2 ) do { print "." ; #y = add ( #y 1 ) ; } ; '
            cond = f'{"eq" if until else "lesser"} ( #x {n} )'
            # Post-until uses >= via not-lesser, so n=0 still terminates after one.
            if post and until:
                cond = f'not ( lesser ( #x {n} ) )'
            loop = (f'do {{ {body}}} {"until" if until else "while"} {cond}' if post else
                    f'{"until" if until else "while"} {cond} do {{ {body}}}')
            count = max(1,n) if post else n
            prefix = ''.join(('e' if x%2==0 else 'o') + ('..' if kind>=8 else '')
                             for x in range(1,count+1)) if kind>=4 else ''
            add('loops', f'form-{kind}-bound-{n}',
                f'#x #y : : #x = 0 ; {loop} ; print ":" ; print ( #x ) ; ',
                f'{prefix}:{count}', req='T07 G01 G07 G08 G09 G10',
                basis=f'{"post" if post else "pre"}-test loop performs {count} increments')

    for n in range(1,11):
        rows = [
            ('zero-one-return', f': num #zero ( ) {{ : : return ( {n} ) }} num #id ( #a ) {{ : : return ( #a ) }} : print ( #id ( #zero ( ) ) ) ; ', str(n), 'F03 F05'),
            ('whole-actuals', f': num #f ( #a #b #c ) {{ : : return ( add ( mul ( #a 100 ) add ( mul ( #b 10 ) #c ) ) ) }} : print ( #f ( add ( {n} 1 ) mul ( 1 3 ) neg ( -4 ) ) ) ; ', str((n+1)*100+34), 'F03 F04 F05'),
            ('capture-before-write', f'#g : num #f ( #a #b ) {{ : : return ( add ( mul ( #a 100 ) #b ) ) }} num #bump ( ) {{ : : #g = add ( #g 1 ) ; return ( #g ) }} : #g = {n} ; print ( #f ( #g #bump ( ) ) ) ; print ":" ; print ( #g ) ; ', f'{100*n+n+1}:{n+1}', 'F04 F05 F08'),
            ('actual-order', f': num #f ( #a #b ) {{ : : return ( sub ( #a #b ) ) }} num #left ( ) {{ : : print "l" ; return ( {n} ) }} num #right ( ) {{ : : print "r" ; return ( {n+2} ) }} : print ( #f ( #left ( ) #right ( ) ) ) ; ', 'lr-2', 'F03 F04 F05'),
            ('parent-local', f'#x : num #f ( #a ) {{ #x : void #g ( ) {{ : : #x = add ( #x 1 ) ; return }} : #x = #a ; #g ( ) ; return ( #x ) }} : #x = 90 ; print ( #f ( {n} ) ) ; print ":" ; print ( #f ( {n+5} ) ) ; print ":" ; print ( #x ) ; ', f'{n+1}:{n+6}:90', 'N01 N02 N09 F06 F07 F08'),
            ('grandparent', f'#global : num #f ( #a ) {{ #local : void #g ( ) {{ : void #h ( ) {{ : : #local = add ( #local 2 ) ; #global = add ( #global 1 ) ; return }} : #h ( ) ; return }} : #local = #a ; #g ( ) ; return ( #local ) }} : #global = 0 ; print ( #f ( {n} ) ) ; print ":" ; print ( #global ) ; ', f'{n+2}:1', 'N01 N02 F01 F06 F08'),
            ('repeated-loop', f': num #f ( #a ) {{ #i : : #i = 0 ; while lesser ( #i #a ) do {{ #i = add ( #i 1 ) ; }} ; return ( #i ) }} : print ( add ( #f ( {n} ) #f ( {n+1} ) ) ) ; ', str(2*n+1), 'F05 F07 G09 G10'),
            ('void-and-inactive', f'#x : void #f ( #p ) {{ : : #x = add ( #x #p ) ; return }} void #unused ( ) {{ : : print "bad" ; #x = 99 ; return }} : #x = 1 ; #f ( {n} ) ; print ( #x ) ; ', str(n+1), 'T04 F01 F02 F05 F08'),
            ('float-return', f': num #f ( #a ) {{ : : return ( div ( #a 2 ) ) }} : print ( #f ( {n} ) ) ; ', format(n/2,'.6g'), 'T03 T06 G05 G06 F05'),
        ]
        for scenario, source, stdout, req in rows:
            add('calls', f'{scenario}-{n}', source, stdout, req=req,
                basis='explicit argument values, lexical binding and sequential side effects; D02/D04/D05 where applicable')

    for n in range(1,11):
        rows = [
            ('siblings', f': num #f ( ) {{ #x : : #x = {n} ; return ( #x ) }} num #g ( ) {{ #x : : #x = {n+20} ; return ( #x ) }} : print ( sub ( #g ( ) #f ( ) ) ) ; ', '20', 'N01 N02 N03 N09 N10'),
            ('same-child-name', f': num #f ( #a ) {{ : num #f ( #a ) {{ : : return ( add ( #a 1 ) ) }} : return ( #f ( #a ) ) }} : print ( #f ( {n} ) ) ; ', str(n+1), 'N02 N06 N07 N08 N09 N10 F06 F08'),
            ('bare-prefix', f'# #x #xx : : # = {n} ; #x = add ( # 1 ) ; #xx = add ( #x 1 ) ; print ( sub ( #xx # ) ) ; ', '2', 'N02 N09 N10 G04'),
        ]
        for scenario, source, stdout, req in rows:
            add('scopes', f'{scenario}-{n}', source, stdout, req=req)

    bad = [
        ('duplicate-local', '#x #x : : ', 7, 'NAME-DUPLICATE-VARIABLE', 'N04 N10'),
        ('duplicate-param', ': void #f ( #a #a ) { : : return } : ', 7, 'NAME-DUPLICATE-PARAMETER', 'N04 N10'),
        ('own-param-mask', ': num #f ( #a ) { #a : : return ( #a ) } : ', 7, 'NAME-PARAMETER-MASK', 'N05 N10'),
        ('overload', ': void #f ( ) { : : return } void #f ( #a ) { : : return } : ', 7, 'NAME-DUPLICATE-FUNCTION', 'N07 N10'),
        ('undeclared', ': : #x = 1 ; ', 7, 'NAME-UNDECLARED-VARIABLE', 'N02 N10'),
        ('sibling-variable', ': void #f ( ) { #x : : return } void #g ( ) { : : #x = 1 ; return } : ', 7, 'NAME-UNDECLARED-VARIABLE', 'N03 N10'),
        ('self-call', ': void #f ( ) { : : #f ( ) ; return } : ', 7, 'NAME-INVISIBLE-FUNCTION', 'N06 N08 N10'),
        ('sibling-call', ': void #f ( ) { : : #g ( ) ; return } void #g ( ) { : : return } : ', 7, 'NAME-INVISIBLE-FUNCTION', 'N06 N08 N10'),
        ('grandchild-call', ': void #f ( ) { : void #g ( ) { : : return } : return } : #g ( ) ; ', 7, 'NAME-INVISIBLE-FUNCTION', 'N06 N10'),
        ('procedure-assignment', '#x : void #p ( ) { : : return } : #x = #p ( ) ; ', 8, 'TYPE-TERM-CALL', 'T04 T05'),
        ('procedure-print', ': void #p ( ) { : : return } : print ( #p ( ) ) ; ', 8, 'TYPE-TERM-CALL', 'T04 T08'),
        ('procedure-arithmetic', ': void #p ( ) { : : return } : print ( add ( 1 #p ( ) ) ) ; ', 8, 'TYPE-TERM-CALL', 'T04 T06'),
        ('procedure-actual', ': void #p ( ) { : : return } void #q ( #a ) { : : return } : #q ( #p ( ) ) ; ', 8, 'TYPE-TERM-CALL', 'T03 T04'),
        ('procedure-return', ': void #p ( ) { : : return } num #q ( ) { : void #p ( ) { : : return } : return ( #p ( ) ) } : ', 8, 'TYPE-TERM-CALL', 'T04 T10'),
        ('num-instruction', ': num #f ( ) { : : return ( 1 ) } : #f ( ) ; ', 8, 'TYPE-INSTR-CALL', 'T02 T04'),
        ('procedure-comparison', ': void #p ( ) { : : return } : if eq ( #p ( ) 1 ) then { } else { } ; ', 8, 'TYPE-TERM-CALL', 'T04 T07'),
        ('procedure-loop', ': void #p ( ) { : : return } : while lesser ( #p ( ) 1 ) do { } ; ', 8, 'TYPE-TERM-CALL', 'T04 T07'),
        ('unresolved-return', ': num #f ( ) { : : return ( #missing ) } : ', 7, 'NAME-UNDECLARED-VARIABLE', 'N02 N10 T10'),
    ]
    for depth in range(5):
        for scenario, source, status, code, req in bad:
            add('rejections', f'{scenario}-uncalled-depth-{depth}', _wrap(source,depth),
                status=status, code=code, req=req+' T09 T10', profile='reject',
                basis='single stated name/type violation, including never-called nested bodies')

    for depth in range(5):
        numeric = [
            ('mod-div', ': : print ( add ( mod ( 5 2 ) div ( 5 2 ) ) ) ; ', 8, 'FLOAT-INT-CONFLICT'),
            ('uncalled-mod-div', ': num #f ( ) { : : return ( mod ( 5 2 ) ) } num #g ( ) { : : return ( div ( 5 2 ) ) } : ', 8, 'FLOAT-INT-CONFLICT'),
            ('decimal-mod', ': : print ( add ( mod ( 5 2 ) 0.5 ) ) ; ', 8, 'DECIMAL-WITH-MOD'),
            ('uncalled-decimal-mod', ': num #f ( ) { : : return ( 0.5 ) } : print ( mod ( 5 2 ) ) ; ', 8, 'DECIMAL-WITH-MOD'),
        ]
        for scenario, source, status, code in numeric:
            add('numeric', f'{scenario}-depth-{depth}', _wrap(source,depth), status=status,
                code=code, req='T06 T10 G06', profile='reject', basis='whole-tree numeric-mode rule')
        add('numeric', f'strings-not-operators-{depth}',
            f': : comment "div.mod.2.1" ; print "div.mod.2.1:" ; print ( mod ( {5+depth} 2 ) ) ; ',
            f'div.mod.2.1:{(5+depth)%2}', req='T06 G02 G03 G06', basis='string text does not select numeric mode')
        add('numeric', f'fractional-div-{depth}',
            f'#x : : #x = div ( {5+2*depth} 2 ) ; print ( #x ) ; ',
            format((5+2*depth)/2,'.6g'), req='T05 T06 G04 G05 G06', basis='division selects float storage even with integer NUM lexemes')

    for n in range(3):
        prefix = '\n'*n
        rows = [
            ('dollar', ': : $ ',4,'LEX-DOLLAR'),
            ('tab', ':\t: ',4,'LEX-TAB'),
            ('separator', ': : nop ;',4,'LEX-NO-SEPARATOR'),
            ('leading-zero', ': : print ( 01 ) ; ',4,'LEX-NUM-LEADING-ZERO'),
            ('negative-zero', ': : print ( -0 ) ; ',4,'LEX-NUM-NEG-ZERO'),
            ('trailing-zero', ': : print ( 1.20 ) ; ',4,'LEX-NUM-TRAILING-ZERO'),
            ('uppercase-string', ': : print "A" ; ',4,'LEX-STRING-CHAR'),
            ('uppercase-name', '#A : : ',4,'LEX-NAME-UPPER'),
            ('semicolon', ': : nop ',5,'SYN-EXPECTED'),
            ('closing-brace', ': : if eq ( 1 1 ) then { nop ; ',5,'SYN-EXPECTED'),
        ]
        for scenario, source, status, code in rows:
            add('frontend', f'{scenario}-line-{n+1}', prefix+source, status=status, code=code,
                req='G01', profile='reject', basis='P1 lexical or grammar boundary; line offset varies')

    for n in range(5):
        rows = [
            ('lex', ': : $ ',4,'LEX-DOLLAR'),
            ('syntax', ': : nop ',5,'SYN-EXPECTED'),
            ('name', ': : print ( #x ) ; ',7,'NAME-UNDECLARED-VARIABLE'),
            ('type', ': num #f ( ) { : : return ( 1 ) } : #f ( ) ; ',8,'TYPE-INSTR-CALL'),
            ('arity', ': void #f ( #a ) { : : return } : #f ( ) ; ',9,'GEN-ARITY'),
        ]
        for scenario, source, status, code in rows:
            add('lifecycle', f'recovery-{scenario}-{n}', '\n'*(n+6)+source, str(n+11),
                status=status, code=code, req='N10 T10 G01 F05', profile='recovery',
                basis='success -> failed full compile clears both outputs -> success/native output')
    for n in range(3):
        for j, alias in enumerate(('xml-direct','target-direct','xml-hardlink','target-hardlink','xml-relative')):
            add('lifecycle', f'{alias}-{n}', f': : print ( {n*5+j+31} ) ; ', str(n*5+j+31),
                req='G01', profile=alias, basis='input/output alias preflight preserves source and prior outputs')
    for n in range(10):
        add('lifecycle', f'xml-roundtrip-{n}',
            f'#x : num #f ( #a ) {{ : : return ( add ( #a 1 ) ) }} : #x = #f ( {n+41} ) ; print ( #x ) ; ',
            str(n+42), req='N09 T01 T09 F03 F05', profile='xml-roundtrip',
            basis='P1 XML retains tree identity and recompiles to identical target')

    for offset in range(5):
        depth=1100+offset
        add('deep', f'term-{depth}', ': : print ( '+'neg ( '*depth+'1 '+') '*depth+') ; ',
            str((-1)**depth), req='T06 G05', basis='negation parity, no source-nesting limit in grammar')
        add('deep', f'bool-{depth}', ': : if '+'not ( '*depth+'eq ( 1 1 ) '+') '*depth+
            'then { print "t" ; } else { print "f" ; } ; ', 't' if depth%2==0 else 'f',
            req='T07 G07 G08', basis='not parity, complete target jump lowering')
        d=350+offset
        add('deep', f'branch-{d}', ': : '+'if eq ( 1 1 ) then { '*d+
            f'print ( {offset+51} ) ; '+'} else { } ; '*d, str(offset+51),
            req='T07 G07 G10', basis='all true branch conditions select one innermost print')
        add('deep', f'post-until-{d}', ': : '+'do { '*d+f'print ( {offset+61} ) ; '+
            '} until eq ( 1 1 ) ; '*d, str(offset+61), req='T07 G09 G10',
            basis='each post-until body runs exactly once')
        d=260+offset
        body=f': : print ( {offset+71} ) ; '
        for _ in range(d):
            body=f': void #f ( ) {{ {body} return }} : #f ( ) ; '
        add('deep', f'function-{d}', body, str(offset+71), req='N01 N06 N08 F01 F02 F06 F07',
            basis='strict child-only same-spelling functions, one final print, inactive code mine')
        d=350+offset
        add('deep', f'actual-{d}', ': num #id ( #a ) { : : return ( #a ) } : print ( '+
            '#id ( '*d+f'{offset+81} '+') '*d+') ; ', str(offset+81),
            req='T03 F03 F04 F05 F07', basis='identity composition returns the deepest argument')

    assert len(cases)==500, len(cases)
    assert len({c.case_id for c in cases})==500
    assert len({c.source for c in cases})==500, 'Cases must have distinct input sources'
    expected = {'arithmetic':50,'booleans':50,'loops':50,'calls':90,'scopes':30,
                'rejections':90,'numeric':30,'frontend':30,'lifecycle':50,'deep':30}
    assert Counter(c.family for c in cases)==expected
    required = {f'{prefix}{i:02d}' for prefix, end in (('N',10),('T',10),('G',10),('F',8))
                for i in range(1,end+1)}
    assert {requirement for c in cases for requirement in c.requirements} == required
    return tuple(cases)


CASES = build_cases()
