"""Deterministic edge matrix with independent expectations and explicit axes."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import re
from collections import Counter

LAYOUTS = ('space','lf','cr','crlf','mixed')


@dataclass(frozen=True)
class EdgeCase:
    case_id: str
    family: str
    scenario: str
    source: str
    stdout: str = ''
    status: int = 0
    code: str = ''
    requirements: tuple[str,...] = ()
    fault_offset: int | None = None
    partner: str | None = None
    profile: str = 'execute'
    policy: str = ''

    def inventory(self) -> dict:
        return {'id':self.case_id,'family':self.family,'scenario':self.scenario,
                'source_sha256':hashlib.sha256(self.source.encode()).hexdigest(),
                'bytes':len(self.source.encode()),'stdout':self.stdout,'status':self.status,
                'code':self.code,'requirements':list(self.requirements),
                'fault_position':list(position(self.source,self.fault_offset)) if self.fault_offset is not None else None,
                'partner_sha256':hashlib.sha256(self.partner.encode()).hexdigest() if self.partner else None,
                'profile':self.profile,'provisional_policy':self.policy}


def position(source: str, offset: int) -> tuple[int,int]:
    """Independent position oracle: CRLF is one newline, CR and LF also work."""
    parts=re.split(r'\r\n|\r|\n',source[:offset])
    return len(parts),len(parts[-1])+1


def layout(template: str, variant: int) -> tuple[str,int | None]:
    # « is a factory marker, never a source character. Literal test token text
    # (including malformed strings) is inserted after formatting at HOLE.
    pieces=[('', '\n ', '\r\r ', '\r\n\r\n', ' \r\n  ')[variant]]
    fault=None
    separators=(' ','\n','\r','\r\n')
    for i,token in enumerate(template.replace('«',' « ').split()):
        if token=='«':
            fault=sum(map(len,pieces));continue
        separator=separators[variant] if variant<4 else ('  ','\r\n ','\r','\n  ')[i%4]
        pieces.extend((token,separator))
    return ''.join(pieces),fault


def wrap(template: str, depth: int) -> str:
    for i in range(depth):template=f': void #enclosure{i} ( ) {{ {template} return }} : '
    return template


def _bool_source(expr) -> str:
    op,*args=expr
    if op=='atom':return f'eq ( #probe ( {args[0]} ) 1 )'
    if op=='cmp':return f'{args[0]} ( #probe ( {args[1]} ) #probe ( {args[2]} ) )'
    return f'{op} ( '+ ' '.join(_bool_source(arg) for arg in args)+' )'


def _bool_value(expr, trace: list[str]) -> bool:
    op,*args=expr
    if op=='atom':trace.append(str(args[0]));return args[0]==1
    if op=='cmp':
        operator,a,b=args;trace.extend((str(a),str(b)))
        return {'eq':a==b,'lesser':a<b,'larger':a>b}[operator]
    if op=='not':return not _bool_value(args[0],trace)
    if op=='and':return _bool_value(args[0],trace) and _bool_value(args[1],trace)
    return _bool_value(args[0],trace) or _bool_value(args[1],trace)


def build_cases() -> tuple[EdgeCase,...]:
    cases=[]
    def add(family,scenario,template,stdout='',*,variant=0,status=0,code='',req='',partner=None,profile='execute',policy=''):
        source,fault=layout(template,variant)
        good=layout(partner,variant)[0] if partner is not None else None
        cases.append(EdgeCase(f'EDGE{len(cases)+1:05d}',family,f'{scenario}/{LAYOUTS[variant]}',source,
                              stdout,status,code,tuple(req.split()),fault,good,profile,policy))

    # 12 expression topologies × ten signed/zero/boundary operand pairs × five layouts.
    for a,b in ((-31,7),(-17,-5),(-1,1),(0,3),(1,-3),(2,5),(17,4),(31,-7),(63,8),(127,9)):
        q=(abs(a)//abs(b))*(-1 if (a<0)!=(b<0) else 1)
        rows=[('add',f'add ( {a} {b} )',a+b),('sub',f'sub ( {a} {b} )',a-b),
              ('mul',f'mul ( {a} {b} )',a*b),('mod',f'mod ( {a} {b} )',a-q*b),
              ('div',f'div ( {a} 2 )',a/2),('neg',f'neg ( {a} )',-a),
              ('nested-left',f'add ( mul ( {a} {b} ) {b} )',a*b+b),
              ('nested-right',f'sub ( {a} mul ( {b} {b} ) )',a-b*b),
              ('balanced',f'mul ( add ( {a} {b} ) sub ( {a} {b} ) )',(a+b)*(a-b)),
              ('self-right',f'add ( {b} #edge )',b+a),
              ('nested-remainder',f'neg ( mod ( {a} {b} ) )',-(a-q*b)),
              ('double-neg',f'neg ( neg ( add ( {a} {b} ) ) )',a+b)]
        for name,expr,result in rows:
            for v in range(5):
                value=a+result
                add('arithmetic',f'{name}/a={a}/b={b}',f'#edge : : #edge = {a} ; #edge = add ( #edge {expr} ) ; '
                    'comment "edge-calculation.!" ; nop ; print "r:" ; print ( #edge ) ; ',
                    'r:'+format(value,'.6g'),variant=v,req='T01 T02 T05 T06 T08 G01 G02 G03 G04 G05 G06')

    for a,b in ((0,0),(0,1),(1,0),(1,1),(-1,2),(2,-1)):
        x,y=('atom',a),('atom',b)
        expressions=[x,('not',x),('and',x,y),('or',x,y),('not',('and',x,y)),('not',('or',x,y)),
                     ('and',('not',x),y),('or',('not',x),y),('and',x,('not',y)),('or',x,('not',y)),
                     ('or',('and',x,y),('not',x)),('and',('or',x,y),('not',y)),
                     ('cmp','eq',a,b),('cmp','lesser',a,b),('cmp','larger',a,b)]
        for i,expr in enumerate(expressions):
            trace=[];truth=_bool_value(expr,trace)
            template=': num #probe ( #arg ) { : : print ( #arg ) ; return ( #arg ) } : '
            template+=f'if {_bool_source(expr)} then {{ print ":t" ; }} else {{ print ":f" ; }} ; print ":" ; print ( {b} ) ; '
            for v in range(5):add('booleans',f'formula={i}/a={a}/b={b}',template,''.join(trace)+(':t' if truth else ':f')+f':{b}',
                                 variant=v,req='T03 T04 T07 G07 G08 G10 F03 F04 F05',policy='D03/D04 short circuit and ordered operand evaluation')

    for n in (0,1,2,3,5,8):
        for kind in range(15):
            form=kind%4;post=form>=2;until=form in (1,3)
            count=max(1,n) if post else n
            declarations='#edge #inner #checks'
            functions='num #probe ( ) { : : #checks = add ( #checks 1 ) ; return ( #edge ) } ' if 8<=kind<12 else ''
            term='#probe ( )' if functions else '#edge'
            condition=f'not ( lesser ( {term} {n} ) )' if until else f'lesser ( {term} {n} )'
            body='#edge = add ( #edge 1 ) ; '
            prefix=''
            if 4<=kind<8:
                body+='if eq ( mod ( #edge 2 ) 0 ) then { print "e" ; } else { print "o" ; } ; '
                prefix=''.join('e' if x%2==0 else 'o' for x in range(1,count+1))
            loop=f'do {{ {body}}} {"until" if until else "while"} {condition}' if post else f'{"until" if until else "while"} {condition} do {{ {body}}}'
            suffix=f':{count}'
            template=f'{declarations} : {functions}: #edge = 0 ; #checks = 0 ; {loop} ; print ":" ; print ( #edge ) ; '
            if functions:
                checks=count if post else count+1
                template+='print ":" ; print ( #checks ) ; ';suffix+=f':{checks}'
            if kind==12:
                template=f'#edge #inner : : #edge = 0 ; while lesser ( #edge {n} ) do {{ #inner = 0 ; do {{ print "i" ; #inner = add ( #inner 1 ) ; }} until not ( lesser ( #inner {n} ) ) ; #edge = add ( #edge 1 ) ; }} ; print ":" ; print ( #edge ) ; '
                prefix='i'*(n*max(1,n));suffix=f':{n}'
            elif kind==13:
                template=f': num #count ( #n ) {{ #i : : #i = 0 ; do {{ #i = add ( #i 1 ) ; }} while lesser ( #i #n ) ; return ( #i ) }} : print ( #count ( {n} ) ) ; print ":" ; print ( #count ( {n+1} ) ) ; '
                prefix='';suffix=f'{max(1,n)}:{n+1}'
            elif kind==14:
                template=f'#edge : : #edge = 0 ; do {{ if lesser ( #edge {n} ) then {{ #edge = add ( #edge 1 ) ; }} else {{ #edge = add ( #edge 2 ) ; }} ; }} until not ( lesser ( #edge {n} ) ) ; print ( #edge ) ; '
                prefix='';suffix=str(n if n else 2)
            for v in range(5):add('loops',f'pattern={kind}/bound={n}',template,prefix+suffix,variant=v,req='T07 G01 G07 G08 G09 G10 F05')

    for n in (1,2,3,7,11):
        rows=call_rows(n)
        assert len(rows)==26,len(rows)
        for name,template,output in rows:
            req='N01 N02 N06 N09 T03 T04 F01 F02 F03 F05'
            if name not in ('zero','inactive','condition-recheck'):req+=' F04'
            if name in ('parent-local','grandparent','shadowed-global','return-child','same-function-child','return-ancestor','return-after-write'):req+=' F06 F08'
            if name in ('nested-actual','parent-local','loop-fresh','void','comment-mine'):req+=' F07'
            for v in range(5):add('calls',f'{name}/n={n}',template,output,variant=v,
                req=req,policy='D02/D04/D06 current argument/namespace interpretation')
        rows=scope_rows(n)
        assert len(rows)==14,len(rows)
        for name,template,output in rows:
            req='N01 N02 N09 N10 T09'
            if name in ('siblings','cousin-global'):req+=' N03'
            if name not in ('root-bare','prefix','long-name','wide-decls','body-control-same-scope'):req+=' N06 F08'
            if name=='child-function-name':req+=' N07 N08'
            for v in range(5):add('scopes',f'{name}/n={n}',template,output,variant=v,req=req,policy='D06 where variable/function spelling coincides')

    append_negative_cases(cases,add)
    append_lifecycle_cases(add)
    expected={'arithmetic':600,'booleans':450,'loops':450,'calls':650,'scopes':350,
              'lexical':800,'syntax':450,'semantic':900,'numeric':200,'lifecycle':150}
    assert Counter(c.family for c in cases)==expected,Counter(c.family for c in cases)
    assert len(cases)==5000
    hashes=[c.inventory()['source_sha256'] for c in cases]
    assert len(set(hashes))==5000,'Duplicate source in expanded corpus'
    assert len({c.case_id for c in cases})==5000
    required={f'{p}{i:02d}' for p,n in (('N',10),('T',10),('G',10),('F',8)) for i in range(1,n+1)}
    assert {r for c in cases for r in c.requirements}==required
    return tuple(cases)


def call_rows(n: int) -> list[tuple[str,str,str]]:
    rows=[]
    def r(name,source,out):rows.append((name,source,str(out)))
    r('zero',f': num #c ( ) {{ : : return ( {n} ) }} : print ( #c ( ) ) ; ',n)
    r('one',f': num #id ( #a ) {{ : : return ( #a ) }} : print ( #id ( add ( {n} 1 ) ) ) ; ',n+1)
    r('two-ordered',f': num #f ( #a #b ) {{ : : return ( sub ( #a #b ) ) }} : print ( #f ( {n} {n+3} ) ) ; ',-3)
    r('three-whole-terms',f': num #f ( #a #b #c ) {{ : : return ( add ( mul ( #a 100 ) add ( mul ( #b 10 ) #c ) ) ) }} : print ( #f ( add ( {n} 1 ) mul ( 2 3 ) neg ( -4 ) ) ) ; ',(n+1)*100+64)
    params=' '.join(f'#p{i}' for i in range(10));actuals=' '.join(str(n+i) for i in range(10))
    r('wide-input',f': num #f ( {params} ) {{ : : return ( sub ( #p9 #p0 ) ) }} : print ( #f ( {actuals} ) ) ; ',9)
    r('nested-actual',': num #id ( #a ) { : : return ( #a ) } : print ( '+'#id ( '*(n+3)+f'{n} '+') '*(n+3)+') ; ',n)
    r('capture',f'#g : num #join ( #a #b ) {{ : : return ( add ( mul ( #a 100 ) #b ) ) }} num #bump ( ) {{ : : #g = add ( #g 1 ) ; return ( #g ) }} : #g = {n} ; print ( #join ( #g #bump ( ) ) ) ; print ":" ; print ( #g ) ; ',f'{101*n+1}:{n+1}')
    r('ltr',f': num #join ( #a #b ) {{ : : return ( add ( #a #b ) ) }} num #left ( ) {{ : : print "l" ; return ( {n} ) }} num #right ( ) {{ : : print "r" ; return ( {n+1} ) }} : print ( #join ( #left ( ) #right ( ) ) ) ; ',f'lr{2*n+1}')
    r('parent-local',f'#g : num #parent ( #a ) {{ #v : void #child ( ) {{ : : #v = add ( #v 2 ) ; return }} : #v = #a ; #child ( ) ; return ( #v ) }} : #g = 90 ; print ( #parent ( {n} ) ) ; print ":" ; print ( #parent ( {n+4} ) ) ; print ":" ; print ( #g ) ; ',f'{n+2}:{n+6}:90')
    r('grandparent',f'#g : num #parent ( #a ) {{ #v : void #child ( ) {{ : void #grand ( ) {{ : : #v = add ( #v 2 ) ; #g = add ( #g 1 ) ; return }} : #grand ( ) ; return }} : #v = #a ; #child ( ) ; return ( #v ) }} : #g = 0 ; print ( #parent ( {n} ) ) ; print ":" ; print ( #g ) ; ',f'{n+2}:1')
    r('shadowed-global',f'#g : num #parent ( #g ) {{ : void #child ( ) {{ : : #g = add ( #g 3 ) ; return }} : #child ( ) ; return ( #g ) }} : #g = 90 ; print ( #parent ( {n} ) ) ; print ":" ; print ( #g ) ; ',f'{n+3}:90')
    r('loop-fresh',f': num #f ( #a ) {{ #i : : #i = 0 ; while lesser ( #i #a ) do {{ #i = add ( #i 1 ) ; }} ; return ( #i ) }} : print ( add ( #f ( {n} ) #f ( {n+2} ) ) ) ; ',2*n+2)
    r('void',f'#g : void #f ( #a ) {{ : : #g = add ( #g #a ) ; return }} : #g = 0 ; #f ( {n} ) ; #f ( {n+1} ) ; print ( #g ) ; ',2*n+1)
    r('inactive',f': void #cold ( ) {{ : : print "never" ; return }} num #warm ( ) {{ : : return ( {n} ) }} : print ( #warm ( ) ) ; ',n)
    r('return-child',f': num #f ( #a ) {{ : num #g ( #b ) {{ : : return ( mul ( #b 2 ) ) }} : return ( #g ( add ( #a 1 ) ) ) }} : print ( #f ( {n} ) ) ; ',2*(n+1))
    r('float',f': num #f ( #a ) {{ #v : : #v = div ( #a 4 ) ; return ( #v ) }} : print ( #f ( {n} ) ) ; ',format(n/4,'.6g'))
    r('same-function-child',f': num #f ( #a ) {{ : num #f ( #a ) {{ : : return ( add ( #a 4 ) ) }} : return ( #f ( #a ) ) }} : print ( #f ( {n} ) ) ; ',n+4)
    r('same-var-function',f'#f : num #f ( #f ) {{ : : return ( add ( #f 5 ) ) }} : #f = {n} ; print ( #f ( #f ) ) ; print ":" ; print ( #f ) ; ',f'{n+5}:{n}')
    r('call-in-bool',f': num #f ( #a ) {{ : : return ( #a ) }} : if larger ( #f ( {n} ) 0 ) then {{ print "yes" ; }} else {{ print "no" ; }} ; ','yes')
    r('condition-recheck',f'#i : num #f ( ) {{ : : return ( #i ) }} : #i = 0 ; while lesser ( #f ( ) {n} ) do {{ #i = add ( #i 1 ) ; }} ; print ( #i ) ; ',n)
    r('comparison-order',f': num #f ( #a ) {{ : : print ( #a ) ; return ( #a ) }} : if lesser ( #f ( {n} ) #f ( {n+1} ) ) then {{ print "t" ; }} else {{ print "f" ; }} ; ',f'{n}{n+1}t')
    r('short-circuit',f': num #f ( #a ) {{ : : print "bad" ; return ( #a ) }} : if or ( eq ( {n} {n} ) eq ( #f ( 1 ) 1 ) ) then {{ print "t" ; }} else {{ print "f" ; }} ; ','t')
    r('return-ancestor',f'#g : num #f ( #a ) {{ : num #child ( ) {{ : : return ( add ( #a #g ) ) }} : return ( #child ( ) ) }} : #g = {n+8} ; print ( #f ( {n} ) ) ; ',2*n+8)
    r('return-after-write',f': num #f ( #a ) {{ : void #write ( ) {{ : : #a = mul ( #a 2 ) ; return }} : #write ( ) ; return ( #a ) }} : print ( #f ( {n} ) ) ; ',2*n)
    r('branch-in-template',f': num #f ( #a ) {{ #v : : if lesser ( #a 4 ) then {{ #v = add ( #a 1 ) ; }} else {{ #v = sub ( #a 1 ) ; }} ; return ( #v ) }} : print ( #f ( {n} ) ) ; ',n+1 if n<4 else n-1)
    r('comment-mine',f': num #f ( #a ) {{ : : comment "if:else?!-return.div.mod" ; nop ; print "a" ; return ( #a ) }} : print ( #f ( {n} ) ) ; print ":" ; print ( #f ( {n+1} ) ) ; ',f'a{n}:a{n+1}')
    return rows


def scope_rows(n: int) -> list[tuple[str,str,str]]:
    rows=[]
    def r(name,source,out):rows.append((name,source,str(out)))
    r('root-bare',f'# #sv : : # = {n} ; #sv = add ( # 1 ) ; print ( #sv ) ; ',n+1)
    r('bare-function',f': num # ( #sv ) {{ : : return ( #sv ) }} : print ( # ( {n} ) ) ; ',n)
    r('prefix',f'#sv #svv #svvv : : #sv = {n} ; #svv = add ( #sv 1 ) ; #svvv = add ( #svv 1 ) ; print ( sub ( #svvv #sv ) ) ; ',2)
    name='#'+'a'*(128*n)
    r('long-name',f'{name} #sv : : {name} = {n} ; #sv = {name} ; print ( #sv ) ; ',n)
    names=' '.join(f'#sv{i}' for i in range(30+n))
    r('wide-decls',f'{names} : : #sv{29+n} = {n} ; print ( #sv{29+n} ) ; ',n)
    r('siblings',f': num #a ( ) {{ #sv : : #sv = {n} ; return ( #sv ) }} num #b ( ) {{ #sv : : #sv = {n+30} ; return ( #sv ) }} : print ( sub ( #b ( ) #a ( ) ) ) ; ',30)
    r('cousin-global',f'#sv : num #a ( ) {{ #sv : num #j ( ) {{ : : return ( #sv ) }} : #sv = 20 ; return ( #j ( ) ) }} num #b ( ) {{ : num #k ( ) {{ : : return ( #sv ) }} : return ( #k ( ) ) }} : #sv = {n} ; print ( add ( #a ( ) #b ( ) ) ) ; ',20+n)
    r('parent-param',f': num #a ( #sv ) {{ : num #b ( ) {{ : : return ( #sv ) }} : return ( #b ( ) ) }} : print ( #a ( {n} ) ) ; ',n)
    r('legal-deeper-mask',f': num #a ( #sv ) {{ : num #b ( ) {{ #sv : : #sv = 9 ; return ( #sv ) }} : return ( add ( #sv #b ( ) ) ) }} : print ( #a ( {n} ) ) ; ',n+9)
    r('parameter-deeper-mask',f': num #a ( #sv ) {{ : num #b ( #sv ) {{ : : return ( #sv ) }} : return ( sub ( #b ( 20 ) #sv ) ) }} : print ( #a ( {n} ) ) ; ',20-n)
    r('body-control-same-scope',f'#sv : : #sv = {n} ; if eq ( 1 1 ) then {{ #sv = add ( #sv 1 ) ; }} else {{ nop ; }} ; print ( #sv ) ; ',n+1)
    r('function-variable-domains',f'#sv : num #sv ( #sv ) {{ : : return ( mul ( #sv 3 ) ) }} : #sv = {n} ; print ( #sv ( #sv ) ) ; ',3*n)
    r('child-function-name',f': num #sv ( #a ) {{ : num #sv ( #b ) {{ : : return ( add ( #b 7 ) ) }} : return ( #sv ( #a ) ) }} : print ( #sv ( {n} ) ) ; ',n+7)
    r('grandchild-root',f'#sv : num #a ( ) {{ : num #b ( ) {{ : num #c ( ) {{ : : return ( #sv ) }} : return ( #c ( ) ) }} : return ( #b ( ) ) }} : #sv = {n} ; print ( #a ( ) ) ; ',n)
    return rows


def append_negative_cases(cases,add) -> None:
    # label, literal bad token, valid replacement, expected code, offset within bad token.
    lexical=[
        ('literal-eof','$','1','LEX-DOLLAR',0),
        ('at-sign','@','1','LEX-UNKNOWN',0),('backslash','\\','1','LEX-UNKNOWN',0),
        ('vertical-tab','\x0b','1','LEX-UNKNOWN',0),('form-feed','\x0c','1','LEX-UNKNOWN',0),
        ('nul','\x00','1','LEX-UNKNOWN',0),('del','\x7f','1','LEX-UNKNOWN',0),
        ('tab','\t','1','LEX-TAB',0),('uppercase-name','#Upper','1','LEX-NAME-UPPER',0),
        ('mixed-name','#aB','1','LEX-NAME-UPPER',0),('underscore-name','#a_','1','LEX-NO-SEPARATOR',0),
        ('hyphen-name','#a-b','1','LEX-NO-SEPARATOR',0),('dot-name','#a.b','1','LEX-NO-SEPARATOR',0),
        ('leading-zero','01','1','LEX-NUM-LEADING-ZERO',0),('many-leading-zero','0001','1','LEX-NUM-LEADING-ZERO',0),
        ('negative-leading-zero','-01','1','LEX-NUM-LEADING-ZERO',0),('negative-zero','-0','1','LEX-NUM-NEG-ZERO',0),
        ('trailing-zero','1.20','1','LEX-NUM-TRAILING-ZERO',0),('zero-fraction','0.0','1','LEX-NUM-TRAILING-ZERO',0),
        ('negative-trailing-zero','-0.10','1','LEX-NUM-TRAILING-ZERO',0),
        ('missing-fraction','1.','1','LEX-NUM-DECIMAL',0),('minus-only','-','1','LEX-NUM-INVALID',0),
        ('dot-leading','.5','1','LEX-UNKNOWN',0),('plus-sign','+1','1','LEX-UNKNOWN',0),
        ('exponent','1e2','1','LEX-NO-SEPARATOR',0),('double-dot','1.2.3','1','LEX-NO-SEPARATOR',0),
        ('merged-number','1)','1','LEX-NO-SEPARATOR',0),('merged-open','(1','1','LEX-NO-SEPARATOR',0),
        ('unknown-word','addition','1','LEX-UNKNOWN-WORD',0),('uppercase-keyword','ADD','1','LEX-UNKNOWN-WORD',0),
        ('unicode-name','#é','1','LEX-NON-ASCII',1),('unicode-digit','١','1','LEX-NON-ASCII',0),
        ('unicode-minus','−1','1','LEX-NON-ASCII',0),('nbsp','\xa0','1','LEX-NON-ASCII',0),
        ('string-uppercase','"A"','"ok"','LEX-STRING-CHAR',1),
        ('string-space','"a b"','"ok"','LEX-STRING-CHAR',2),
        ('string-tab','"a\tb"','"ok"','LEX-STRING-CHAR',2),
        ('string-newline','"a\nb"','"ok"','LEX-STRING-NEWLINE',2),
        ('string-forbidden','"a/b"','"ok"','LEX-STRING-CHAR',2),
        ('string-unicode','"aé"','"ok"','LEX-NON-ASCII',2),
    ]
    assert len(lexical)==40
    for name,bad,good,code,delta in lexical:
        output='print HOLE ; ' if good.startswith('"') else 'print ( HOLE ) ; '
        contexts=[f'#lex : : #lex = 3 ; {output}',
                  f'#lex : void #cold ( ) {{ : : {output}return }} : #lex = 3 ; ',
                  f'#lex : : #lex = 3 ; if eq ( #lex 3 ) then {{ {output}}} else {{ nop ; }} ; ',
                  f'#lex : : #lex = 0 ; while lesser ( #lex 1 ) do {{ {output}#lex = add ( #lex 1 ) ; }} ; ']
        for context,template in enumerate(contexts):
            for v in range(5):
                marked=template.replace('HOLE','«HOLE')
                source,offset=layout(marked,v)
                partner=source.replace('HOLE',good,1)
                source=source.replace('HOLE',bad,1)
                cases.append(EdgeCase(f'EDGE{len(cases)+1:05d}','lexical',f'{name}/context={context}/{LAYOUTS[v]}',
                    source,status=4,code=code,requirements=('G01','T10'),fault_offset=offset+delta,
                    partner=partner,profile='reject'))

    syntax=[
        ('missing-colon', '#syn : « ', '#syn : : '),
        ('missing-section', '#syn : «nop ; ', '#syn : : nop ; '),
        ('missing-semicolon', ': : print ( 3 ) «print ( 4 ) ; ', ': : print ( 3 ) ; print ( 4 ) ; '),
        ('assign-no-equal', '#syn : : #syn «3 ; ', '#syn : : #syn = 3 ; '),
        ('assign-no-term', '#syn : : #syn = «; ', '#syn : : #syn = 3 ; '),
        ('print-open', ': : print «3 ) ; ', ': : print ( 3 ) ; '),
        ('print-close', ': : print ( 3 «; ', ': : print ( 3 ) ; '),
        ('binary-open', ': : print ( add «3 4 ) ) ; ', ': : print ( add ( 3 4 ) ) ; '),
        ('binary-rhs', ': : print ( add ( 3 «) ) ; ', ': : print ( add ( 3 4 ) ) ; '),
        ('binary-extra', ': : print ( add ( 3 4 «5 ) ) ; ', ': : print ( add ( 3 4 ) ) ; '),
        ('unary-extra', ': : print ( neg ( 3 «4 ) ) ; ', ': : print ( neg ( 3 ) ) ; '),
        ('bool-missing', ': : if «then { } else { } ; ', ': : if eq ( 1 1 ) then { } else { } ; '),
        ('bool-term', ': : if «1 then { } else { } ; ', ': : if eq ( 1 1 ) then { } else { } ; '),
        ('then-missing', ': : if eq ( 1 1 ) «{ } else { } ; ', ': : if eq ( 1 1 ) then { } else { } ; '),
        ('then-open', ': : if eq ( 1 1 ) then «nop ; } else { } ; ', ': : if eq ( 1 1 ) then { nop ; } else { } ; '),
        ('else-missing', ': : if eq ( 1 1 ) then { } «{ } ; ', ': : if eq ( 1 1 ) then { } else { } ; '),
        ('else-open', ': : if eq ( 1 1 ) then { } else «nop ; } ; ', ': : if eq ( 1 1 ) then { } else { nop ; } ; '),
        ('while-do', ': : while lesser ( 1 0 ) «{ } ; ', ': : while lesser ( 1 0 ) do { } ; '),
        ('until-open', ': : until eq ( 1 1 ) do «nop ; } ; ', ': : until eq ( 1 1 ) do { nop ; } ; '),
        ('post-condition', ': : do { } «eq ( 1 1 ) ; ', ': : do { } until eq ( 1 1 ) ; '),
        ('post-bool', ': : do { } until «; ', ': : do { } until eq ( 1 1 ) ; '),
        ('function-name', ': void «( ) { : : return } : ', ': void #f ( ) { : : return } : '),
        ('formal-open', ': void #f «) { : : return } : ', ': void #f ( ) { : : return } : '),
        ('formal-close', ': void #f ( «{ : : return } : ', ': void #f ( ) { : : return } : '),
        ('body-open', ': void #f ( ) «: : return } : ', ': void #f ( ) { : : return } : '),
        ('return-missing', ': void #f ( ) { : : «} : ', ': void #f ( ) { : : return } : '),
        ('numeric-return-open', ': num #f ( ) { : : return «3 ) } : ', ': num #f ( ) { : : return ( 3 ) } : '),
        ('numeric-return-empty', ': num #f ( ) { : : return ( «) } : ', ': num #f ( ) { : : return ( 3 ) } : '),
        ('call-close', ': void #f ( ) { : : return } : #f ( «; ', ': void #f ( ) { : : return } : #f ( ) ; '),
        ('extra-end', ': : nop ; «) ', ': : nop ; '),
    ]
    for depth in range(3):
        for name,bad,good in syntax:
            for v in range(5):add('syntax',f'{name}/depth={depth}',wrap(bad,depth),status=5,
                code='SYN-NAME-FOLLOW' if name=='assign-no-equal' else 'SYN-EXPECTED',variant=v,
                partner=wrap(good,depth),profile='reject',req='G01 T09')

    for depth in range(6):
        for name,bad,good,code,req in semantic_rows():
            for v in range(5):add('semantic',f'{name}/depth={depth}',wrap(bad.replace('#a','#semarg').replace('#f','#semf'),depth),status=7 if code.startswith('NAME') else 8,
                code=code,variant=v,partner=wrap(good.replace('#a','#semarg').replace('#f','#semf'),depth),profile='reject',req=req+' T09 T10')

    for depth in range(4):
        rows=[
            ('both-root', ': : print ( add ( «mod ( 5 2 ) div ( 5 2 ) ) ) ; ', 'FLOAT-INT-CONFLICT'),
            ('separate-functions', ': num #a ( ) { : : return ( «mod ( 5 2 ) ) } num #b ( ) { : : return ( div ( 5 2 ) ) } : ', 'FLOAT-INT-CONFLICT'),
            ('div-first', ': : print ( add ( div ( 5 2 ) «mod ( 5 2 ) ) ) ; ', 'FLOAT-INT-CONFLICT'),
            ('cold-child-conflict', ': void #cold ( ) { : : print ( add ( «mod ( 5 2 ) div ( 5 2 ) ) ) ; return } : ', 'FLOAT-INT-CONFLICT'),
            ('decimal-root', ': : print ( add ( mod ( 5 2 ) «0.25 ) ) ; ', 'DECIMAL-WITH-MOD'),
            ('decimal-return', ': num #f ( ) { : : return ( «0.25 ) } : print ( mod ( 5 2 ) ) ; ', 'DECIMAL-WITH-MOD'),
            ('negative-decimal', ': : print ( add ( mod ( 5 2 ) «-0.25 ) ) ; ', 'DECIMAL-WITH-MOD'),
            ('cold-decimal', ': void #cold ( ) { : : print ( «0.25 ) ; return } : print ( mod ( 5 2 ) ) ; ', 'DECIMAL-WITH-MOD'),
        ]
        for name,bad,code in rows:
            bad=bad.replace(': : ',': : nop ; ',1)
            good=bad.replace('«','').replace('mod','add')
            for v in range(5):add('numeric',f'{name}/depth={depth}',wrap(bad,depth),status=8,code=code,variant=v,
                partner=wrap(good,depth),req='T06 T10 G06',profile='reject')
        for v in range(5):
            add('numeric',f'ignore-string-operators/depth={depth}',
                f': num #cold ( ) {{ : : return ( {depth+3} ) }} : print "mod.div.0.25:" ; print ( mod ( {depth+5} 2 ) ) ; ',
                f'mod.div.0.25:{(depth+5)%2}',variant=v,req='T06 G02 G03 G06')
            add('numeric',f'float-storage/depth={depth}',
                f'#mode : num #half ( #n ) {{ : : return ( div ( #n 2 ) ) }} : #mode = #half ( {depth+5} ) ; print ( #mode ) ; ',
                format((depth+5)/2,'.6g'),variant=v,req='T03 T05 T06 G04 G05 G06 F05',policy='D05 output/mode')


def semantic_rows():
    rows=[]
    def r(name,bad,good,code,req):rows.append((name,bad,good,code,req))
    r('duplicate-adjacent','#decl #decl «#decl : : ','#decl #other #third : : ','NAME-DUPLICATE-VARIABLE','N04 N10')
    # The first duplicate must be the marked token, not an earlier unmarked copy.
    rows[-1]=(rows[-1][0],'#decl «#decl : : ',*rows[-1][2:])
    r('duplicate-nonadjacent','#decl #other «#decl : : ','#decl #other #third : : ','NAME-DUPLICATE-VARIABLE','N04 N10')
    r('duplicate-formal',': void #f ( #a «#a ) { : : return } : ',': void #f ( #a #b ) { : : return } : ','NAME-DUPLICATE-PARAMETER','N04 N10')
    r('duplicate-formal-wide',': void #f ( #a #b «#a ) { : : return } : ',': void #f ( #a #b #c ) { : : return } : ','NAME-DUPLICATE-PARAMETER','N04 N10')
    r('mask-first',': void #f ( #a ) { «#a : : return } : ',': void #f ( #a ) { #b : : return } : ','NAME-PARAMETER-MASK','N05 N10')
    r('mask-later',': void #f ( #a #b ) { #c «#b : : return } : ',': void #f ( #a #b ) { #c #d : : return } : ','NAME-PARAMETER-MASK','N05 N10')
    for name,second in (('same-void','void #f ( ) { : : return }'),('mixed-return','num #f ( ) { : : return ( 1 ) }'),('overloaded','void #f ( #a ) { : : return }')):
        bad=': void #f ( ) { : : return } '+second.replace('#f','«#f',1)+' : '
        good=bad.replace('«#f','#g')
        r(name,bad,good,'NAME-DUPLICATE-FUNCTION','N07 N10')
    r('undeclared-write',': : «#missing = 4 ; ','#missing : : #missing = 4 ; ','NAME-UNDECLARED-VARIABLE','N02 N10')
    r('undeclared-read',': : print ( «#missing ) ; ','#missing : : #missing = 4 ; print ( #missing ) ; ','NAME-UNDECLARED-VARIABLE','N02 N10')
    r('sibling-variable',': void #a ( ) { #missing : : return } void #b ( ) { : : print ( «#missing ) ; return } : ',
      '#missing : void #a ( ) { #missing : : return } void #b ( ) { : : print ( #missing ) ; return } : ','NAME-UNDECLARED-VARIABLE','N03 N10')
    r('cousin-variable',': void #a ( ) { : void #j ( ) { #missing : : return } : return } void #b ( ) { : void #k ( ) { : : print ( «#missing ) ; return } : return } : ',
      '#missing : void #a ( ) { : void #j ( ) { #missing : : return } : return } void #b ( ) { : void #k ( ) { : : print ( #missing ) ; return } : return } : ','NAME-UNDECLARED-VARIABLE','N03 N10')
    r('self-call',': void #f ( ) { : : «#f ( ) ; return } : ',': void #f ( ) { : void #g ( ) { : : return } : #g ( ) ; return } : ','NAME-INVISIBLE-FUNCTION','N06 N08 N10')
    r('sibling-call',': void #a ( ) { : : «#b ( ) ; return } void #b ( ) { : : return } : ',': void #a ( ) { : void #b ( ) { : : return } : #b ( ) ; return } void #b ( ) { : : return } : ','NAME-INVISIBLE-FUNCTION','N06 N08 N10')
    r('grandchild-call',': void #a ( ) { : void #b ( ) { : : return } : return } : «#b ( ) ; ',': void #a ( ) { : void #b ( ) { : : return } : #b ( ) ; return } : #a ( ) ; ','NAME-INVISIBLE-FUNCTION','N06 N10')
    r('ancestor-call',': void #a ( ) { : void #b ( ) { : : «#a ( ) ; return } : return } : ',': void #a ( ) { : void #b ( ) { : : nop ; return } : return } : ','NAME-INVISIBLE-FUNCTION','N06 N08 N10')
    head='#typed : void #p ( ) { : : return } : '
    contexts=[('assign','#typed = «#p ( ) ; '),('print','print ( «#p ( ) ) ; '),
              ('neg','print ( neg ( «#p ( ) ) ) ; '),('binary-left','print ( add ( «#p ( ) 1 ) ) ; '),
              ('binary-right','print ( add ( 1 «#p ( ) ) ) ; '),
              ('comparison-left','if eq ( «#p ( ) 1 ) then { } else { } ; '),
              ('comparison-right','if eq ( 1 «#p ( ) ) then { } else { } ; '),
              ('composed','if not ( or ( eq ( 1 2 ) eq ( «#p ( ) 1 ) ) ) then { } else { } ; '),
              ('while','while lesser ( «#p ( ) 1 ) do { } ; '),
              ('post-until','do { } until eq ( «#p ( ) 1 ) ; ')]
    for name,body in contexts:
        bad=head+body
        good=bad.replace('«','').replace('void #p ( ) { : : return }','num #p ( ) { : : return ( 1 ) }')
        req='T04 '+('T05' if name=='assign' else 'T08' if name=='print' else 'T06' if name in ('neg','binary-left','binary-right') else 'T07')
        r('void-'+name,bad,good,'TYPE-TERM-CALL',req)
    bad=': void #p ( ) { : : return } void #q ( #a ) { : : return } : #q ( «#p ( ) ) ; '
    r('void-actual',bad,bad.replace('«','').replace('void #p ( ) { : : return }','num #p ( ) { : : return ( 1 ) }'),'TYPE-TERM-CALL','T03 T04')
    bad=': num #q ( ) { : void #p ( ) { : : return } : return ( «#p ( ) ) } : '
    r('void-return',bad,bad.replace('«','').replace('void #p ( ) { : : return }','num #p ( ) { : : return ( 1 ) }'),'TYPE-TERM-CALL','T02 T04 T10')
    r('num-instruction',': num #q ( ) { : : return ( 1 ) } : «#q ( ) ; ',': num #q ( ) { : : return ( 1 ) } : print ( #q ( ) ) ; ','TYPE-INSTR-CALL','T02 T04')
    assert len(rows)==30,len(rows)
    return rows


def append_lifecycle_cases(add) -> None:
    # Five failure phases × five layouts; each includes valid -> bad -> valid.
    rows=[('lex',': : «$ ',4,'LEX-DOLLAR'),('syntax',': : print ( 1 «; ',5,'SYN-EXPECTED'),
          ('name',': : print ( «#missing ) ; ',7,'NAME-UNDECLARED-VARIABLE'),
          ('type',': num #q ( ) { : : return ( 1 ) } : «#q ( ) ; ',8,'TYPE-INSTR-CALL'),
          ('arity',': void #f ( #a ) { : : return } : «#f ( ) ; ',9,'GEN-ARITY')]
    for name,bad,status,code in rows:
        for v in range(5):
            # Add a different valid instruction prefix, preserving the marked fault.
            template=wrap(bad,1).replace('#enclosure0','#recover')
            add('lifecycle',f'recovery-{name}',template,str(v+101),status=status,code=code,variant=v,
                profile='recovery',req='N10 T10 G01 F05',policy='D04 for arity')
    profiles=('xml-direct','target-direct','xml-hardlink','target-hardlink','xml-relative',
              'outputs-hardlink','xml-symlink-input','target-symlink-input','stale-xml-symlink','stale-target-symlink',
              'missing-input','directory-input','xml-is-directory','target-is-directory','empty-input',
              'xml-roundtrip','determinism','frontend-only','repeated-api','xml-invalid')
    for i,profile in enumerate(profiles):
        for v in range(5):
            number=200+i*5+v
            add('lifecycle',profile,f'#life : num #lifef ( #p ) {{ : : return ( add ( #p 1 ) ) }} : #life = #lifef ( {number} ) ; print ( #life ) ; ',
                str(number+1),variant=v,profile=profile,req='N09 T01 T09 G01 F01 F05')
    # Five compiler error phases, with a non-default filename containing spaces.
    for name,bad,status,code in rows:
        for v in range(5):add('lifecycle',f'explicit-path-{name}',wrap(bad,2).replace('#enclosure','#explicit'),str(v+301),status=status,code=code,
                variant=v,profile='explicit-recovery',req='N10 T10 G01 F05',policy='D04 for arity')


CASES=build_cases()
