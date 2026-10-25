"""Part 2a name binding over the existing, read-only SPL concrete tree.

Collect declarations before uses, then bind in source traversal order. Variables
search current/ancestor scopes; calls search only the caller P's direct F_DECL.
No type, arity, definite-assignment or code-generation policy is imposed here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import re
from types import MappingProxyType

from spl_frontend.semantic_model import (
    FoundationError, ResolvedProgram, SourceSpan, Symbol, SymbolKind, SymbolTable,
)
from spl_frontend.source_map import SourceMap
from spl_frontend.tree import NodeKind, SyntaxTree, TreeNode
from spl_frontend.tree_walkers import (
    FunctionParts, function_parts, iter_list_items, iter_preorder, program_parts,
)


class NameAnalysisError(ValueError):
    """A naming violation with a real source span or an XML/tree node ID."""

    def __init__(
        self, code: str, name: str, rule: str, hint: str, *, node_id: int,
        path: Path | None = None, span: SourceSpan | None = None,
        related_node_id: int | None = None, related_span: SourceSpan | None = None,
    ) -> None:
        self.code = code
        self.name = name
        self.rule = rule
        self.message = f"{name!r}: {rule}"
        self.hint = hint
        self.node_id = node_id
        self.span = span
        self.path = span.path if span is not None else path
        self.related_node_id = related_node_id
        self.related_span = related_span
        super().__init__(self.message)

    def render(self) -> str:
        location = str(self.path) if self.path is not None else "tree"
        if self.span is not None:
            location += f":{self.span.line}:{self.span.column}"
        else:
            location += f":node[{self.node_id}]"
        return f"{location}: name[{self.code}]: {self.message}\nhint: {self.hint}"


def _require_shape(tree: SyntaxTree, node: TreeNode, labels: tuple[str | None, ...]) -> None:
    """Check the local name-bearing production, not a second SPL parser."""
    if len(node.child_ids) != len(labels):
        raise FoundationError("TREE-SHAPE", f"Invalid {node.contents} shape.", node_id=node.node_id)
    for child_id, label in zip(node.child_ids, labels):
        child = tree.get_node(child_id)
        inner = label in {"INPUT", "TERM", "P"}
        if child.kind is not (NodeKind.INNER if inner else NodeKind.LEAF) or (
            label is not None and child.contents != label
        ):
            raise FoundationError("TREE-SHAPE", f"Invalid {node.contents} child.", node_id=child_id)


def _call_name(tree: SyntaxTree, node: TreeNode) -> TreeNode:
    _require_shape(tree, node, (None, "(", "INPUT", ")"))
    name = tree.get_node(node.child_ids[0])
    if not re.fullmatch(r"#[a-z0-9]*", name.contents):
        raise FoundationError("TREE-SHAPE", "CALL must start with a user-defined name.", node_id=name.node_id)
    return name


class _Resolver:
    def __init__(self, tree: SyntaxTree, locations: SourceMap) -> None:
        self.tree = tree
        self.locations = locations
        self.table = SymbolTable()
        self.bindings: dict[int, int] = {}
        self.functions: dict[int, tuple[FunctionParts, int]] = {}

    def fail(
        self, code: str, node: TreeNode, rule: str, hint: str,
        previous: Symbol | None = None,
    ) -> None:
        raise NameAnalysisError(
            code, node.contents, rule, hint, node_id=node.node_id,
            path=self.locations.path, span=self.locations.span_for(node.node_id),
            related_node_id=previous.declaration_node_id if previous else None,
            related_span=self.locations.span_for(previous.declaration_node_id) if previous else None,
        )

    def declare(self, scope_id: int, kind: SymbolKind, node: TreeNode) -> Symbol:
        if kind is SymbolKind.FUNCTION:
            previous = self.table.lookup_function(scope_id, node.contents)
        else:
            previous = self.table.lookup_variable(scope_id, node.contents)
            if previous is not None and previous.scope_id != scope_id:
                previous = None  # Legal deeper shadowing of an ancestor.
        if previous is not None:
            if kind is SymbolKind.FUNCTION:
                code = "NAME-DUPLICATE-FUNCTION"
                rule = "function names in one F_DECL must be unique; overloading is forbidden."
            elif previous.kind is SymbolKind.PARAMETER and kind is SymbolKind.VARIABLE:
                code = "NAME-PARAMETER-MASK"
                rule = "a function body local may not mask that function's own parameter."
            elif kind is SymbolKind.PARAMETER:
                code = "NAME-DUPLICATE-PARAMETER"
                rule = "parameters of one function must have distinct names."
            else:
                code = "NAME-DUPLICATE-VARIABLE"
                rule = "variables in one declaration scope must have distinct names."
            self.fail(code, node, rule, "Remove or rename the duplicate declaration.", previous)
        symbol = self.table.declare(scope_id, kind, node.contents, node.node_id)
        self.bindings[node.node_id] = symbol.symbol_id
        return symbol

    def collect(self, root_p: TreeNode) -> int:
        root_scope = self.table.add_scope(root_p.node_id)
        # Each task carries the owning function's already-declared identity.
        pending: list[tuple[TreeNode, int, int | None, TreeNode | None]] = [
            (root_p, root_scope.scope_id, None, None)
        ]
        while pending:
            p_node, scope_id, function_id, parameters = pending.pop()
            parameter_ids = tuple(
                self.declare(scope_id, SymbolKind.PARAMETER, node).symbol_id
                for node in iter_list_items(self.tree, parameters.node_id)
            ) if parameters is not None else ()
            if function_id is not None:
                self.table.set_function_signature(function_id, scope_id, parameter_ids)
            parts = program_parts(self.tree, p_node.node_id)
            for node in iter_list_items(self.tree, parts.variables.node_id):
                self.declare(scope_id, SymbolKind.VARIABLE, node)
            children = []
            for node in iter_list_items(self.tree, parts.functions.node_id):
                function = function_parts(self.tree, node.node_id)
                symbol = self.declare(scope_id, SymbolKind.FUNCTION, function.name)
                body_scope = self.table.add_scope(function.body.node_id, scope_id)
                self.functions[node.node_id] = (function, body_scope.scope_id)
                children.append((function.body, body_scope.scope_id,
                                 symbol.symbol_id, function.parameters))
            pending.extend(reversed(children))
        return root_scope.scope_id

    def resolve(self, root_scope_id: int) -> ResolvedProgram:
        assert self.tree.root is not None
        scopes: dict[int, int] = {}
        pending = [(self.tree.root.node_id, root_scope_id)]
        p_nodes = {s.p_node_id for s in self.table.scopes.values()}
        while pending:
            node_id, scope_id = pending.pop()
            node = self.tree.get_node(node_id)
            scopes[node_id] = scope_id
            if node.kind is NodeKind.INNER and node.contents == "F_TYPE":
                if node_id not in self.functions:
                    raise FoundationError("TREE-SHAPE", "F_TYPE is outside an owning F_DECL.", node_id=node_id)
                _, body_scope_id = self.functions[node_id]
                # Declaration keyword/name belong to the enclosing P; the
                # parameter list, body and return expression use its child scope.
                pending.extend((child, scope_id if index < 2 else body_scope_id)
                               for index, child in reversed(list(enumerate(node.child_ids))))
                continue
            if node.kind is NodeKind.INNER and node.contents == "P" and node_id not in p_nodes:
                raise FoundationError("TREE-SHAPE", "P is outside a function body/root.", node_id=node_id)
            if node.kind is NodeKind.INNER and node.contents == "CALL":
                _call_name(self.tree, node)
                # INPUT yields top-level arguments, not their nested operands.
                # Arity checking belongs to later work.
                tuple(iter_list_items(self.tree, node.child_ids[2]))
            if node.kind is NodeKind.LEAF and re.fullmatch(r"#[a-z0-9]*", node.contents):
                if node_id not in self.bindings:
                    self.bind_use(node, scope_id)
            pending.extend((child, scope_id) for child in reversed(node.child_ids))
        resolved = ResolvedProgram(
            self.tree, self.table.scopes, self.table.symbols, scopes, self.bindings,
            self.locations.source_location_by_node,
        )
        build_call_hierarchy(resolved)  # Protective visibility/cycle boundary.
        return resolved

    def bind_use(self, node: TreeNode, scope_id: int) -> None:
        assert node.parent_id is not None
        parent = self.tree.get_node(node.parent_id)
        if parent.contents == "CALL":
            _call_name(self.tree, parent)
            if parent.child_ids[0] != node.node_id:
                raise FoundationError("TREE-SHAPE", "CALL name must be its first child.", node_id=node.node_id)
            symbol = self.table.lookup_function(scope_id, node.contents)
            if symbol is None:
                self.fail(
                    "NAME-INVISIBLE-FUNCTION", node,
                    "a call requires a function in the caller P's immediate F_DECL.",
                    "Declare a direct child function; self, sibling, ancestor and deeper-descendant calls are forbidden.",
                )
        elif parent.contents in {"ASSIGN", "TERM"}:
            labels = (None, "=", "TERM") if parent.contents == "ASSIGN" else (None,)
            _require_shape(self.tree, parent, labels)
            if parent.child_ids[0] != node.node_id:
                raise FoundationError("TREE-SHAPE", "Variable must be the first child.", node_id=node.node_id)
            symbol = self.table.lookup_variable(scope_id, node.contents)
            if symbol is None:
                self.fail(
                    "NAME-UNDECLARED-VARIABLE", node,
                    "a variable requires a declaration in its current scope or an ancestor.",
                    "Declare the variable in V_DECL or a parameter list; sibling/cousin declarations are not visible.",
                )
        else:
            raise FoundationError("TREE-NAME-CONTEXT", "Name is outside a declaration, variable use or call.", node_id=node.node_id)
        assert symbol is not None
        self.bindings[node.node_id] = symbol.symbol_id


def resolve_names(
    tree: SyntaxTree, source_map: SourceMap | None = None, *, path: Path | None = None,
) -> ResolvedProgram:
    """Bind all declarations/uses, including uncalled bodies and return TERM.

    The release uses distinct variable/function namespaces, introducing no
    extra cross-kind rejection, and return TERM uses the function body scope.
    With XML only, pass path=xml_path; diagnostics use node IDs, not fake lines.
    """
    if path is not None and not isinstance(path, Path):
        raise ValueError("Input path must be a Path.")
    if source_map is not None and not isinstance(source_map, SourceMap):
        raise ValueError("Expected a SourceMap.")
    if source_map is not None and path is not None and source_map.path != path:
        raise ValueError("Input path and source map path disagree.")
    locations = source_map if source_map is not None else SourceMap(path or Path("tree.xml"), {})
    try:
        tree.validate()
    except ValueError as exc:
        raise FoundationError("TREE-INVALID", str(exc), path=locations.path) from exc
    node_ids = {n.node_id for n in tree.iter_nodes()}
    if set(locations.source_location_by_node) - node_ids:
        raise FoundationError("MAP-NODE", "Source map contains nodes outside this tree.", path=locations.path)
    root = tree.root
    assert root is not None
    _require_shape(tree, root, ("P",))
    resolver = _Resolver(tree, locations)
    root_scope_id = resolver.collect(tree.get_node(root.child_ids[0]))
    return resolver.resolve(root_scope_id)


@dataclass(frozen=True, slots=True)
class CallHierarchy:
    """Actual call edges; None denotes main, other keys are function symbol IDs."""

    callees_by_caller: Mapping[int | None, tuple[int, ...]]
    bottom_up_function_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "callees_by_caller", MappingProxyType(
            {caller: tuple(callees) for caller, callees in self.callees_by_caller.items()}
        ))


def build_call_hierarchy(program: ResolvedProgram) -> CallHierarchy:
    """Derive a deterministic, cycle-checked inliner handoff, including unused functions.

    Each callee precedes its caller in bottom_up_function_ids. Repeated calls
    produce one edge; call-site bindings remain in program.binding_by_name_node.
    Revalidate direct-child visibility if a consumer supplies a modified snapshot.
    """
    functions = [s for s in program.symbols.values() if s.kind is SymbolKind.FUNCTION]
    owner_by_scope = {s.body_scope_id: s.symbol_id for s in functions}
    graph: dict[int | None, dict[int, int]] = {None: {}}
    graph.update((s.symbol_id, {}) for s in functions)
    sites: list[tuple[TreeNode, int, Symbol]] = []
    for node in iter_preorder(program.tree):
        if node.kind is not NodeKind.INNER or node.contents != "CALL":
            continue
        name = _call_name(program.tree, node)
        symbol = program.symbols[program.binding_by_name_node[name.node_id]]
        if symbol.kind is not SymbolKind.FUNCTION:
            raise FoundationError("TREE-CALL-BINDING", "CALL must bind to a function.", node_id=name.node_id)
        scope_id = program.scope_by_node[node.node_id]
        caller_id = owner_by_scope.get(scope_id)
        if caller_id is None and program.scopes[scope_id].parent_id is not None:
            raise FoundationError("TREE-SCOPE", "Call scope has no owning function.", node_id=node.node_id)
        graph[caller_id].setdefault(symbol.symbol_id, name.node_id)
        sites.append((name, scope_id, symbol))

    state: dict[int, int] = {}
    bottom_up = []
    for function in functions:
        start = function.symbol_id
        if state.get(start):
            continue
        state[start] = 1
        pending = [(start, iter(graph[start].items()))]
        while pending:
            caller, children = pending[-1]
            edge = next(children, None)
            if edge is None:
                state[caller] = 2
                bottom_up.append(caller)
                pending.pop()
                continue
            callee, node_id = edge
            if state.get(callee) == 1:
                name = program.tree.get_node(node_id)
                raise NameAnalysisError(
                    "NAME-RECURSION", name.contents,
                    "direct and indirect functional recursion are forbidden.",
                    "Remove the cycle and call only direct child functions.",
                    node_id=node_id, span=program.source_location_by_node.get(node_id),
                )
            if not state.get(callee):
                state[callee] = 1
                pending.append((callee, iter(graph[callee].items())))
    for name, scope_id, symbol in sites:
        if symbol.scope_id != scope_id:
            raise NameAnalysisError(
                "NAME-INVISIBLE-FUNCTION", name.contents,
                "a call requires a function in the caller P's immediate F_DECL.",
                "Bind the call to a direct child function.", node_id=name.node_id,
                span=program.source_location_by_node.get(name.node_id),
            )
    return CallHierarchy({caller: tuple(edges) for caller, edges in graph.items()}, tuple(bottom_up))
