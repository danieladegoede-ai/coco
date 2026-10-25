"""Shared P2 identities and annotations; no name/type analysis is run here.

SymbolTable is a per-compilation builder. ResolvedProgram and CheckedProgram
copy their mappings into read-only snapshots for downstream consumers. The
existing SyntaxTree remains the P1 tree and must be treated as read-only.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
import re
from types import MappingProxyType

from spl_frontend.tree import NodeKind, SyntaxTree


def _positive(value: int, label: str) -> None:
    if type(value) is not int or value < 1:
        raise ValueError(f"{label} must be a positive integer.")


class SemanticType(str, Enum):
    UNKNOWN = "unknown"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    PROCEDURE = "procedure"
    OK = "ok"


class NumericMode(str, Enum):
    INTEGER = "int"
    FLOAT = "float"


class SymbolKind(str, Enum):
    VARIABLE = "variable"
    PARAMETER = "parameter"
    FUNCTION = "function"


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """Original one-based positions and zero-based, end-exclusive offsets."""

    path: Path
    line: int
    column: int
    offset: int
    end_line: int
    end_column: int
    end_offset: int

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            raise ValueError("Source span path must be a Path.")
        for label in ("line", "column", "end_line", "end_column"):
            _positive(getattr(self, label), label)
        for label in ("offset", "end_offset"):
            value = getattr(self, label)
            if type(value) is not int or value < 0:
                raise ValueError(f"{label} must be a non-negative integer.")
        if self.end_offset < self.offset or (
            self.end_line, self.end_column
        ) < (self.line, self.column):
            raise ValueError("Source span ends before it starts.")


class FoundationError(ValueError):
    """Structured tree/XML/alignment failure without invented source positions."""

    def __init__(
        self, code: str, message: str, *, path: Path | None = None,
        node_id: int | None = None, span: SourceSpan | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.path = span.path if span else path
        self.node_id = node_id
        self.span = span

    def render(self) -> str:
        location = str(self.path) if self.path is not None else "tree"
        if self.span is not None:
            location += f":{self.span.line}:{self.span.column}"
        elif self.node_id is not None:
            location += f":node[{self.node_id}]"
        return f"{location}: tree[{self.code}]: {self.message}"


@dataclass(frozen=True, slots=True)
class Scope:
    scope_id: int
    parent_id: int | None
    p_node_id: int
    depth: int

    def __post_init__(self) -> None:
        _positive(self.scope_id, "scope ID")
        _positive(self.p_node_id, "P node ID")
        if type(self.depth) is not int or self.depth < 0:
            raise ValueError("Scope depth must be a non-negative integer.")
        if self.parent_id is None:
            if self.depth != 0:
                raise ValueError("A root scope must have depth zero.")
        else:
            _positive(self.parent_id, "parent scope ID")
            if self.parent_id == self.scope_id or self.depth == 0:
                raise ValueError("A child scope needs a different parent and positive depth.")


@dataclass(frozen=True, slots=True)
class Symbol:
    symbol_id: int
    kind: SymbolKind
    declaration_node_id: int
    scope_id: int
    original_name: str
    internal_name: str
    value_type: SemanticType = SemanticType.UNKNOWN
    parameter_ids: tuple[int, ...] = ()
    body_scope_id: int | None = None

    def __post_init__(self) -> None:
        for label in ("symbol_id", "declaration_node_id", "scope_id"):
            _positive(getattr(self, label), label)
        if not isinstance(self.kind, SymbolKind):
            raise ValueError("Invalid symbol kind.")
        if not isinstance(self.value_type, SemanticType):
            raise ValueError("Invalid symbol type.")
        if not isinstance(self.original_name, str) or not re.fullmatch(
            r"#[a-z0-9]*", self.original_name
        ):
            raise ValueError("A symbol needs an SPL user-defined name.")
        if not isinstance(self.internal_name, str) or not re.fullmatch(
            r"[a-zA-Z][a-zA-Z0-9_]*", self.internal_name
        ):
            raise ValueError("Invalid internal identifier.")
        if type(self.parameter_ids) is not tuple:
            raise ValueError("Parameter IDs must be an ordered tuple.")
        for value in self.parameter_ids:
            _positive(value, "parameter ID")
        if len(set(self.parameter_ids)) != len(self.parameter_ids):
            raise ValueError("Duplicate parameter IDs.")
        if self.body_scope_id is not None:
            _positive(self.body_scope_id, "body scope ID")
        if self.kind is not SymbolKind.FUNCTION and (
            self.parameter_ids or self.body_scope_id is not None
        ):
            raise ValueError("Only functions have parameters/body scopes.")
        allowed = {SemanticType.UNKNOWN, SemanticType.NUMERIC}
        if self.kind is SymbolKind.FUNCTION:
            allowed.add(SemanticType.PROCEDURE)
        if self.value_type not in allowed:
            raise ValueError("Symbol kind and semantic type disagree.")


class SymbolTable:
    """Deterministic builder with separate variable and direct-function lookup.

    Separate internal namespaces do not decide whether SPL permits a spelling
    collision between kinds. That language policy belongs to name analysis.
    """

    def __init__(self) -> None:
        self._scopes: dict[int, Scope] = {}
        self._symbols: dict[int, Symbol] = {}
        self._index: dict[tuple[int, bool, str], int] = {}
        self._p_nodes: set[int] = set()
        self._declaration_nodes: set[int] = set()

    @property
    def scopes(self) -> Mapping[int, Scope]:
        return MappingProxyType(self._scopes)

    @property
    def symbols(self) -> Mapping[int, Symbol]:
        return MappingProxyType(self._symbols)

    def add_scope(self, p_node_id: int, parent_id: int | None = None) -> Scope:
        _positive(p_node_id, "P node ID")
        if p_node_id in self._p_nodes:
            raise ValueError(f"P node {p_node_id} already has a scope.")
        if parent_id is None:
            if self._scopes:
                raise ValueError("A symbol table has exactly one root scope.")
            depth = 0
        else:
            depth = self._scope(parent_id).depth + 1
        scope = Scope(len(self._scopes) + 1, parent_id, p_node_id, depth)
        self._scopes[scope.scope_id] = scope
        self._p_nodes.add(p_node_id)
        return scope

    def _scope(self, scope_id: int) -> Scope:
        _positive(scope_id, "scope ID")
        try:
            return self._scopes[scope_id]
        except KeyError as exc:
            raise ValueError(f"Unknown scope {scope_id}.") from exc

    def declare(
        self, scope_id: int, kind: SymbolKind, name: str,
        declaration_node_id: int, *, value_type: SemanticType = SemanticType.UNKNOWN,
    ) -> Symbol:
        self._scope(scope_id)
        if not isinstance(kind, SymbolKind):
            raise ValueError("Invalid symbol kind.")
        _positive(declaration_node_id, "declaration node ID")
        if not isinstance(name, str):
            raise ValueError("A symbol name must be a string.")
        key = (scope_id, kind is SymbolKind.FUNCTION, name)
        if key in self._index:
            raise ValueError(f"Duplicate {kind.value} declaration {name} in scope {scope_id}.")
        if declaration_node_id in self._declaration_nodes:
            raise ValueError(f"Node {declaration_node_id} already declares a symbol.")
        symbol_id = len(self._symbols) + 1
        prefix = {SymbolKind.VARIABLE: "v", SymbolKind.PARAMETER: "p", SymbolKind.FUNCTION: "f"}[kind]
        symbol = Symbol(symbol_id, kind, declaration_node_id, scope_id, name,
                        f"spl_{prefix}{symbol_id}", value_type)
        self._symbols[symbol_id] = symbol
        self._index[key] = symbol_id
        self._declaration_nodes.add(declaration_node_id)
        return symbol

    def ancestors(self, scope_id: int) -> Iterator[Scope]:
        scope = self._scope(scope_id)
        while True:
            yield scope
            if scope.parent_id is None:
                return
            scope = self._scope(scope.parent_id)

    def lookup_variable(self, scope_id: int, name: str) -> Symbol | None:
        for scope in self.ancestors(scope_id):
            symbol_id = self._index.get((scope.scope_id, False, name))
            if symbol_id is not None:
                return self._symbols[symbol_id]
        return None

    def lookup_function(self, scope_id: int, name: str) -> Symbol | None:
        self._scope(scope_id)
        symbol_id = self._index.get((scope_id, True, name))
        return self._symbols.get(symbol_id) if symbol_id is not None else None

    def set_type(self, symbol_id: int, value_type: SemanticType) -> Symbol:
        _positive(symbol_id, "symbol ID")
        updated = replace(self._symbols[symbol_id], value_type=value_type)
        self._symbols[symbol_id] = updated
        return updated

    def set_function_signature(
        self, symbol_id: int, body_scope_id: int, parameter_ids: tuple[int, ...],
    ) -> Symbol:
        _positive(symbol_id, "symbol ID")
        symbol = self._symbols[symbol_id]
        body = self._scope(body_scope_id)
        if symbol.kind is not SymbolKind.FUNCTION or body.parent_id != symbol.scope_id:
            raise ValueError("A function body must be a child of its declaring scope.")
        for parameter_id in parameter_ids:
            _positive(parameter_id, "parameter ID")
            parameter = self._symbols[parameter_id]
            if parameter.kind is not SymbolKind.PARAMETER or parameter.scope_id != body_scope_id:
                raise ValueError("Function parameters must belong to its body scope.")
        updated = replace(symbol, body_scope_id=body_scope_id, parameter_ids=parameter_ids)
        self._symbols[symbol_id] = updated
        return updated


@dataclass(frozen=True, slots=True)
class ResolvedProgram:
    tree: SyntaxTree
    scopes: Mapping[int, Scope]
    symbols: Mapping[int, Symbol]
    scope_by_node: Mapping[int, int]
    binding_by_name_node: Mapping[int, int]
    source_location_by_node: Mapping[int, SourceSpan] = field(default_factory=dict)
    renamed_name_by_node: Mapping[int, str] = field(init=False)

    def __post_init__(self) -> None:
        self.tree.validate()
        for name in ("scopes", "symbols", "scope_by_node", "binding_by_name_node", "source_location_by_node"):
            copied = dict(getattr(self, name))
            for key in copied:
                _positive(key, f"{name} key")
            object.__setattr__(self, name, MappingProxyType(copied))
        if any(not isinstance(s, Scope) for s in self.scopes.values()):
            raise ValueError("Scopes must contain Scope records.")
        if any(not isinstance(s, Symbol) for s in self.symbols.values()):
            raise ValueError("Symbols must contain Symbol records.")
        nodes = {n.node_id: n for n in self.tree.iter_nodes()}
        if set(self.scope_by_node) != set(nodes):
            raise ValueError("Every tree node needs a scope annotation.")
        roots = [s for s in self.scopes.values() if s.parent_id is None]
        if len(roots) != 1:
            raise ValueError("A resolved program needs exactly one root scope.")
        p_nodes: set[int] = set()
        for key, scope in self.scopes.items():
            if key != scope.scope_id or scope.p_node_id in p_nodes:
                raise ValueError("Scope identity or owning P node is duplicated.")
            owner = nodes.get(scope.p_node_id)
            if owner is None or owner.kind is not NodeKind.INNER or owner.contents != "P":
                raise ValueError("Scope owner must be a P node.")
            p_nodes.add(scope.p_node_id)
            if self.scope_by_node[scope.p_node_id] != scope.scope_id:
                raise ValueError("A P node must be annotated with its own scope.")
            if scope.parent_id is not None:
                parent = self.scopes.get(scope.parent_id)
                if parent is None or scope.depth != parent.depth + 1:
                    raise ValueError("Scope parent/depth is inconsistent.")
        if p_nodes != {n.node_id for n in nodes.values() if n.kind is NodeKind.INNER and n.contents == "P"}:
            raise ValueError("Every P node needs exactly one scope.")
        for scope_id in self.scope_by_node.values():
            _positive(scope_id, "node scope ID")
            if scope_id not in self.scopes:
                raise ValueError("Node refers to an unknown scope.")
        internal_names: set[str] = set()
        declaration_nodes: set[int] = set()
        function_bodies: set[int] = set()
        for key, symbol in self.symbols.items():
            declaration = nodes.get(symbol.declaration_node_id)
            if key != symbol.symbol_id or symbol.scope_id not in self.scopes:
                raise ValueError("Invalid symbol identity/scope.")
            if (
                declaration is None
                or declaration.kind is not NodeKind.LEAF
                or declaration.contents != symbol.original_name
            ):
                raise ValueError("Symbol must refer to its original declaration leaf.")
            if symbol.internal_name in internal_names:
                raise ValueError("Internal symbol names must be globally unique.")
            internal_names.add(symbol.internal_name)
            if symbol.declaration_node_id in declaration_nodes:
                raise ValueError("A declaration leaf cannot define two symbols.")
            declaration_nodes.add(symbol.declaration_node_id)
            if symbol.kind is SymbolKind.FUNCTION:
                body = self.scopes.get(symbol.body_scope_id)
                if body is None or body.parent_id != symbol.scope_id:
                    raise ValueError("Function needs a body in a child scope.")
                if body.scope_id in function_bodies:
                    raise ValueError("Functions cannot share a body scope.")
                function_bodies.add(body.scope_id)
                expected_parameters = {
                    s.symbol_id for s in self.symbols.values()
                    if s.kind is SymbolKind.PARAMETER and s.scope_id == body.scope_id
                }
                if set(symbol.parameter_ids) != expected_parameters:
                    raise ValueError("Function signature must include all body parameters.")
                for parameter_id in symbol.parameter_ids:
                    parameter = self.symbols.get(parameter_id)
                    if (
                        parameter is None
                        or parameter.kind is not SymbolKind.PARAMETER
                        or parameter.scope_id != body.scope_id
                    ):
                        raise ValueError("Function parameter does not belong to its body.")
        if any(
            s.kind is SymbolKind.PARAMETER and s.scope_id not in function_bodies
            for s in self.symbols.values()
        ):
            raise ValueError("A parameter must belong to a function body.")
        names = {
            n.node_id for n in nodes.values()
            if n.kind is NodeKind.LEAF and re.fullmatch(r"#[a-z0-9]*", n.contents)
        }
        if set(self.binding_by_name_node) != names:
            raise ValueError("Every name leaf, including declarations, needs a binding.")
        renamed = {}
        for node_id, symbol_id in self.binding_by_name_node.items():
            _positive(symbol_id, "bound symbol ID")
            symbol = self.symbols.get(symbol_id)
            if symbol is None or nodes[node_id].contents != symbol.original_name:
                raise ValueError("Name binding does not match its symbol.")
            renamed[node_id] = symbol.internal_name
        if any(self.binding_by_name_node.get(s.declaration_node_id) != s.symbol_id for s in self.symbols.values()):
            raise ValueError("A declaration must bind to its own symbol.")
        for node_id, span in self.source_location_by_node.items():
            if node_id not in nodes or not isinstance(span, SourceSpan):
                raise ValueError("Invalid node source annotation.")
        object.__setattr__(self, "renamed_name_by_node", MappingProxyType(renamed))


@dataclass(frozen=True, slots=True)
class CheckedProgram:
    resolved: ResolvedProgram
    type_by_node: Mapping[int, SemanticType]
    numeric_mode: NumericMode

    def __post_init__(self) -> None:
        types = dict(self.type_by_node)
        for node_id in types:
            _positive(node_id, "typed node ID")
        if not isinstance(self.numeric_mode, NumericMode):
            raise ValueError("Checked program needs one numeric mode.")
        nodes = {n.node_id: n for n in self.resolved.tree.iter_nodes()}
        if any(
            n not in nodes or not isinstance(t, SemanticType) or t is SemanticType.UNKNOWN
            for n, t in types.items()
        ):
            raise ValueError("Checked annotations must refer to nodes with known types.")
        if any(n.kind is not NodeKind.LEAF and n.node_id not in types for n in nodes.values()):
            raise ValueError("Every non-terminal needs a checked type.")
        root = self.resolved.tree.root
        assert root is not None
        if types[root.node_id] is not SemanticType.OK:
            raise ValueError("Checked program root must be ok.")
        for node_id, symbol_id in self.resolved.binding_by_name_node.items():
            symbol = self.resolved.symbols[symbol_id]
            if symbol.value_type is SemanticType.UNKNOWN or types.get(node_id) is not symbol.value_type:
                raise ValueError("Every bound name needs its checked symbol type.")
        object.__setattr__(self, "type_by_node", MappingProxyType(types))
