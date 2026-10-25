"""Typed, structural intermediate representation for SPL target generation.

The IR deliberately stores symbol and label identities rather than rendered
source fragments.  A :class:`TargetProgram` is a closed executable: every
storage location is declared, every jump target is defined exactly once, and
all user-facing names have already been resolved by semantic analysis.

This module is independent of the SPL parser's concrete spelling except for
validated numeric/string literals.  It has no process-global allocation state.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
from types import MappingProxyType
from typing import TypeAlias

from spl_frontend.semantic_model import NumericMode, SourceSpan, Symbol, SymbolKind


class CodegenError(ValueError):
    """Structured failure raised when target IR invariants are violated."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        node_id: int | None = None,
        path: Path | None = None,
        span: SourceSpan | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.node_id = node_id
        self.span = span
        self.path = span.path if span is not None else path

    def render(self) -> str:
        if self.span is not None:
            location = f"{self.span.path}:{self.span.line}:{self.span.column}: "
        elif self.path is not None:
            node = f":node[{self.node_id}]" if self.node_id is not None else ""
            location = f"{self.path}{node}: "
        else:
            location = f"node[{self.node_id}]: " if self.node_id is not None else ""
        return f"{location}codegen[{self.code}]: {self.message}"



def _positive(value: object, label: str) -> None:
    if type(value) is not int or value < 1:
        raise CodegenError("IR-IDENTITY", f"{label} must be a positive integer.")


class TargetScalarType(str, Enum):
    """Numeric scalar types supported by the selected target dialect."""

    INTEGER = "int"
    FLOAT = "float"

    @classmethod
    def from_mode(cls, mode: NumericMode) -> TargetScalarType:
        if mode is NumericMode.INTEGER:
            return cls.INTEGER
        if mode is NumericMode.FLOAT:
            return cls.FLOAT
        raise CodegenError("IR-NUMERIC-MODE", f"Unsupported numeric mode {mode!r}.")


class StorageKind(str, Enum):
    """Disjoint generated-storage namespaces used by all backend passes."""

    TEMPORARY = "temporary"
    EXPANSION = "expansion"
    CAPTURE = "capture"
    RETURN = "return"


@dataclass(frozen=True, slots=True)
class StorageRef:
    """A structurally identified target storage location owned by the IR."""

    storage_id: int
    kind: StorageKind = StorageKind.TEMPORARY
    value_type: TargetScalarType = TargetScalarType.INTEGER

    def __post_init__(self) -> None:
        _positive(self.storage_id, "storage ID")
        if not isinstance(self.kind, StorageKind):
            raise CodegenError("IR-STORAGE-KIND", "Invalid storage namespace.")
        if not isinstance(self.value_type, TargetScalarType):
            raise CodegenError("IR-STORAGE-TYPE", "Invalid storage scalar type.")


@dataclass(frozen=True, slots=True)
class SymbolRef:
    """Reference to one resolved SPL variable/parameter declaration identity."""

    symbol_id: int

    def __post_init__(self) -> None:
        _positive(self.symbol_id, "symbol ID")


@dataclass(frozen=True, slots=True)
class LabelRef:
    """Reference to a generated control-flow label, never a source spelling."""

    label_id: int

    def __post_init__(self) -> None:
        _positive(self.label_id, "label ID")


_NUMERIC_LITERAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?\Z")


@dataclass(frozen=True, slots=True)
class NumberLiteral:
    """A checked SPL numeric lexeme kept exact until target rendering."""

    lexeme: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.lexeme, str)
            or not _NUMERIC_LITERAL.fullmatch(self.lexeme)
            or self.lexeme == "-0"
        ):
            raise CodegenError("IR-NUMBER-LITERAL", f"Invalid SPL numeric literal {self.lexeme!r}.")


@dataclass(frozen=True, slots=True)
class StringLiteral:
    """String contents without the surrounding SPL quote characters."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise CodegenError("IR-STRING-LITERAL", "String literal value must be text.")


Operand: TypeAlias = SymbolRef | StorageRef | NumberLiteral
StorageLocation: TypeAlias = SymbolRef | StorageRef


class BinaryOperator(str, Enum):
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    MODULO = "%"

    @classmethod
    def from_spl(cls, lexeme: str) -> BinaryOperator:
        try:
            return {
                "add": cls.ADD,
                "sub": cls.SUBTRACT,
                "mul": cls.MULTIPLY,
                "div": cls.DIVIDE,
                "mod": cls.MODULO,
            }[lexeme]
        except KeyError as exc:
            raise CodegenError("IR-OPERATOR", f"Unsupported binary operator {lexeme!r}.") from exc


class UnaryOperator(str, Enum):
    NEGATE = "-"


class CompareOperator(str, Enum):
    EQUAL = "=="
    GREATER = ">"
    LESS = "<"

    @classmethod
    def from_spl(cls, lexeme: str) -> CompareOperator:
        try:
            return {"eq": cls.EQUAL, "larger": cls.GREATER, "lesser": cls.LESS}[lexeme]
        except KeyError as exc:
            raise CodegenError("IR-COMPARATOR", f"Unsupported comparison {lexeme!r}.") from exc


@dataclass(frozen=True, slots=True)
class Assign:
    target: StorageLocation
    value: Operand

    def __post_init__(self) -> None:
        if not isinstance(self.target, (SymbolRef, StorageRef)):
            raise CodegenError("IR-LVALUE", "Assignment target must be a storage location.")
        if not isinstance(self.value, (SymbolRef, StorageRef, NumberLiteral)):
            raise CodegenError("IR-OPERAND", "Assignment value is not an operand.")


@dataclass(frozen=True, slots=True)
class BinaryAssign:
    target: StorageLocation
    operator: BinaryOperator
    left: Operand
    right: Operand

    def __post_init__(self) -> None:
        if not isinstance(self.target, (SymbolRef, StorageRef)):
            raise CodegenError("IR-LVALUE", "Binary assignment target must be a storage location.")
        if not isinstance(self.operator, BinaryOperator):
            raise CodegenError("IR-OPERATOR", "Invalid binary operator.")
        _validate_operand(self.left)
        _validate_operand(self.right)


@dataclass(frozen=True, slots=True)
class UnaryAssign:
    target: StorageLocation
    operator: UnaryOperator
    value: Operand

    def __post_init__(self) -> None:
        if not isinstance(self.target, (SymbolRef, StorageRef)):
            raise CodegenError("IR-LVALUE", "Unary assignment target must be a storage location.")
        if not isinstance(self.operator, UnaryOperator):
            raise CodegenError("IR-OPERATOR", "Invalid unary operator.")
        _validate_operand(self.value)


@dataclass(frozen=True, slots=True)
class PrintNumber:
    value: Operand

    def __post_init__(self) -> None:
        _validate_operand(self.value)


@dataclass(frozen=True, slots=True)
class PrintString:
    value: StringLiteral

    def __post_init__(self) -> None:
        if not isinstance(self.value, StringLiteral):
            raise CodegenError("IR-STRING", "PrintString requires a StringLiteral.")


@dataclass(frozen=True, slots=True)
class Nop:
    """Source ``nop``; intentionally has no runtime effect."""


@dataclass(frozen=True, slots=True)
class Comment:
    """Source comment payload; it must never become executable target code."""

    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise CodegenError("IR-COMMENT", "Comment text must be a string.")


@dataclass(frozen=True, slots=True)
class Label:
    label: LabelRef

    def __post_init__(self) -> None:
        if not isinstance(self.label, LabelRef):
            raise CodegenError("IR-LABEL", "Label instruction requires a LabelRef.")


@dataclass(frozen=True, slots=True)
class Jump:
    target: LabelRef

    def __post_init__(self) -> None:
        if not isinstance(self.target, LabelRef):
            raise CodegenError("IR-JUMP", "Jump target requires a LabelRef.")


@dataclass(frozen=True, slots=True)
class ConditionalJump:
    left: Operand
    operator: CompareOperator
    right: Operand
    true_target: LabelRef
    false_target: LabelRef

    def __post_init__(self) -> None:
        _validate_operand(self.left)
        _validate_operand(self.right)
        if not isinstance(self.operator, CompareOperator):
            raise CodegenError("IR-COMPARATOR", "Conditional jump requires a comparison operator.")
        if not isinstance(self.true_target, LabelRef) or not isinstance(self.false_target, LabelRef):
            raise CodegenError("IR-JUMP", "Conditional jump destinations must be LabelRefs.")


Instruction: TypeAlias = (
    Assign | BinaryAssign | UnaryAssign | PrintNumber | PrintString | Nop | Comment
    | Label | Jump | ConditionalJump
)


def _validate_operand(value: object) -> None:
    if not isinstance(value, (SymbolRef, StorageRef, NumberLiteral)):
        raise CodegenError("IR-OPERAND", f"Invalid operand {value!r}.")


def _target_operands(instruction: Instruction) -> tuple[Operand, ...]:
    if isinstance(instruction, Assign):
        return (instruction.target, instruction.value)
    if isinstance(instruction, BinaryAssign):
        return (instruction.target, instruction.left, instruction.right)
    if isinstance(instruction, UnaryAssign):
        return (instruction.target, instruction.value)
    if isinstance(instruction, PrintNumber):
        return (instruction.value,)
    if isinstance(instruction, ConditionalJump):
        return (instruction.left, instruction.right)
    if isinstance(instruction, (PrintString, Nop, Comment, Label, Jump)):
        return ()
    raise CodegenError("IR-INSTRUCTION", f"Unsupported instruction object {instruction!r}.")


def _label_uses(instruction: Instruction) -> tuple[LabelRef, ...]:
    if isinstance(instruction, Jump):
        return (instruction.target,)
    if isinstance(instruction, ConditionalJump):
        return (instruction.true_target, instruction.false_target)
    return ()


@dataclass(frozen=True, slots=True)
class IRFragment:
    """Ordered executable instructions plus storage owned by the fragment.

    Fragments may reference caller-owned storage and continuation labels, which
    are resolved when the fragments are assembled into a closed TargetProgram.
    """

    declarations: tuple[StorageRef, ...] = ()
    instructions: tuple[Instruction, ...] = ()

    def __post_init__(self) -> None:
        declarations = tuple(self.declarations)
        instructions = tuple(self.instructions)
        if any(not isinstance(item, StorageRef) for item in declarations):
            raise CodegenError("IR-DECLARATION", "Fragment declarations must be StorageRefs.")
        if any(not isinstance(item, (
            Assign, BinaryAssign, UnaryAssign, PrintNumber, PrintString, Nop, Comment,
            Label, Jump, ConditionalJump,
        )) for item in instructions):
            raise CodegenError("IR-INSTRUCTION", "Fragment contains an unknown instruction.")
        keys = [(item.kind, item.storage_id) for item in declarations]
        if len(keys) != len(set(keys)):
            raise CodegenError("IR-DUPLICATE-STORAGE", "Fragment declares storage more than once.")
        object.__setattr__(self, "declarations", declarations)
        object.__setattr__(self, "instructions", instructions)


def combine_fragments(*fragments: IRFragment) -> IRFragment:
    """Concatenate fragments in order, deduplicating identical declarations."""
    declarations: list[StorageRef] = []
    declaration_by_key: dict[tuple[StorageKind, int], StorageRef] = {}
    instructions: list[Instruction] = []
    for fragment in fragments:
        if not isinstance(fragment, IRFragment):
            raise CodegenError("IR-FRAGMENT", "Expected an IRFragment.")
        for declaration in fragment.declarations:
            key = (declaration.kind, declaration.storage_id)
            prior = declaration_by_key.get(key)
            if prior is not None and prior != declaration:
                raise CodegenError("IR-STORAGE-TYPE", f"Storage {key!r} has inconsistent declarations.")
            if prior is None:
                declaration_by_key[key] = declaration
                declarations.append(declaration)
        instructions.extend(fragment.instructions)
    return IRFragment(tuple(declarations), tuple(instructions))


@dataclass(frozen=True, slots=True)
class CodeMineSection:
    """Non-executable, safely line-commented function-template documentation."""

    name: str
    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise CodegenError("IR-CODE-MINE", "Code-mine section needs a non-empty name.")
        if not isinstance(self.text, str):
            raise CodegenError("IR-CODE-MINE", "Code-mine contents must be text.")


@dataclass(frozen=True, slots=True)
class TargetProgram:
    """Closed target executable and metadata required for safe rendering."""

    numeric_mode: NumericMode
    root_scope_id: int
    symbols: Mapping[int, Symbol]
    declared_symbol_ids: tuple[int, ...]
    fragment: IRFragment
    code_mine: tuple[CodeMineSection, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.numeric_mode, NumericMode):
            raise CodegenError("IR-NUMERIC-MODE", "TargetProgram needs a checked NumericMode.")
        _positive(self.root_scope_id, "root scope ID")
        copied_symbols = dict(self.symbols)
        for symbol_id, symbol in copied_symbols.items():
            if type(symbol_id) is not int or symbol_id < 1 or not isinstance(symbol, Symbol):
                raise CodegenError("IR-SYMBOL-TABLE", "TargetProgram has an invalid symbol table entry.")
            if symbol_id != symbol.symbol_id:
                raise CodegenError("IR-SYMBOL-TABLE", "Symbol mapping key does not match symbol identity.")
        symbol_ids = tuple(self.declared_symbol_ids)
        if any(type(symbol_id) is not int or symbol_id < 1 for symbol_id in symbol_ids):
            raise CodegenError("IR-DECLARATION", "Declared symbol IDs must be positive integers.")
        if len(symbol_ids) != len(set(symbol_ids)):
            raise CodegenError("IR-DUPLICATE-SYMBOL", "A symbol is declared more than once.")
        if not isinstance(self.fragment, IRFragment):
            raise CodegenError("IR-FRAGMENT", "TargetProgram needs an IRFragment.")
        code_mine = tuple(self.code_mine)
        if any(not isinstance(section, CodeMineSection) for section in code_mine):
            raise CodegenError("IR-CODE-MINE", "Invalid code-mine section.")
        object.__setattr__(self, "symbols", MappingProxyType(copied_symbols))
        object.__setattr__(self, "declared_symbol_ids", symbol_ids)
        object.__setattr__(self, "code_mine", code_mine)
        self.validate()

    def validate(self) -> None:
        """Validate all symbols, storage uses, labels and control-flow targets."""
        declared_symbols = set(self.declared_symbol_ids)
        for symbol_id in declared_symbols:
            symbol = self.symbols.get(symbol_id)
            if symbol is None:
                raise CodegenError("IR-UNKNOWN-SYMBOL", f"Declared symbol {symbol_id} does not exist.")
            if symbol.kind is not SymbolKind.VARIABLE or symbol.scope_id != self.root_scope_id:
                raise CodegenError(
                    "IR-SYMBOL-SCOPE",
                    f"Only a root-scope variable can be declared directly (symbol {symbol_id}).",
                )
            if symbol.value_type.value != "numeric":
                raise CodegenError("IR-SYMBOL-TYPE", f"Declared symbol {symbol_id} is not numeric.")

        declared_storage: dict[tuple[StorageKind, int], StorageRef] = {
            (storage.kind, storage.storage_id): storage for storage in self.fragment.declarations
        }
        expected_type = TargetScalarType.from_mode(self.numeric_mode)
        for storage in self.fragment.declarations:
            if storage.value_type is not expected_type:
                raise CodegenError(
                    "IR-STORAGE-TYPE",
                    f"Storage {storage.kind.value}_{storage.storage_id} has type {storage.value_type.value}; "
                    f"checked numeric mode requires {expected_type.value}.",
                )

        definitions: set[LabelRef] = set()
        used_labels: set[LabelRef] = set()
        for instruction in self.fragment.instructions:
            if isinstance(instruction, BinaryAssign):
                if instruction.operator is BinaryOperator.MODULO and self.numeric_mode is not NumericMode.INTEGER:
                    raise CodegenError("IR-NUMERIC-MODE", "Modulo requires integer numeric mode.")
                if instruction.operator is BinaryOperator.DIVIDE and self.numeric_mode is not NumericMode.FLOAT:
                    raise CodegenError("IR-NUMERIC-MODE", "Division requires floating numeric mode.")
            if isinstance(instruction, Label):
                if instruction.label in definitions:
                    raise CodegenError(
                        "IR-DUPLICATE-LABEL", f"Label {instruction.label.label_id} is defined more than once."
                    )
                definitions.add(instruction.label)
            used_labels.update(_label_uses(instruction))
            for operand in _target_operands(instruction):
                if isinstance(operand, NumberLiteral):
                    if self.numeric_mode is NumericMode.INTEGER and "." in operand.lexeme:
                        raise CodegenError("IR-NUMERIC-MODE", "A decimal literal requires floating numeric mode.")
                elif isinstance(operand, StorageRef):
                    key = (operand.kind, operand.storage_id)
                    declared = declared_storage.get(key)
                    if declared is None:
                        raise CodegenError(
                            "IR-UNDECLARED-STORAGE",
                            f"Storage {operand.kind.value}_{operand.storage_id} is used but not declared.",
                        )
                    if declared != operand:
                        raise CodegenError(
                            "IR-STORAGE-TYPE",
                            f"Use of storage {operand.kind.value}_{operand.storage_id} disagrees with its declaration.",
                        )
                elif isinstance(operand, SymbolRef):
                    symbol = self.symbols.get(operand.symbol_id)
                    if symbol is None:
                        raise CodegenError("IR-UNKNOWN-SYMBOL", f"Symbol {operand.symbol_id} does not exist.")
                    if symbol.kind not in {SymbolKind.VARIABLE, SymbolKind.PARAMETER}:
                        raise CodegenError(
                            "IR-NON-STORAGE-SYMBOL", f"Function symbol {operand.symbol_id} used as storage."
                        )
                    if operand.symbol_id not in declared_symbols:
                        raise CodegenError(
                            "IR-UNDECLARED-SYMBOL",
                            f"Symbol {operand.symbol_id} is used but has no top-level storage declaration.",
                        )
        missing = used_labels - definitions
        if missing:
            ids = ", ".join(str(label.label_id) for label in sorted(missing, key=lambda item: item.label_id))
            raise CodegenError("IR-UNKNOWN-LABEL", f"Jump target(s) not defined: {ids}.")


class FreshNameAllocator:
    """Deterministic per-compilation label/storage allocator with disjoint kinds."""

    _PREFIXES = {
        StorageKind.TEMPORARY: "spl_tmp",
        StorageKind.EXPANSION: "spl_exp",
        StorageKind.CAPTURE: "spl_cap",
        StorageKind.RETURN: "spl_ret",
    }

    def __init__(self) -> None:
        self._storage_counts: dict[StorageKind, int] = {kind: 0 for kind in StorageKind}
        self._label_count = 0

    def new_storage(
        self,
        kind: StorageKind = StorageKind.TEMPORARY,
        value_type: TargetScalarType = TargetScalarType.INTEGER,
    ) -> StorageRef:
        if not isinstance(kind, StorageKind):
            raise CodegenError("IR-STORAGE-KIND", "Invalid storage namespace.")
        if not isinstance(value_type, TargetScalarType):
            raise CodegenError("IR-STORAGE-TYPE", "Invalid storage scalar type.")
        self._storage_counts[kind] += 1
        return StorageRef(self._storage_counts[kind], kind, value_type)

    def new_temporary(self, value_type: TargetScalarType) -> StorageRef:
        return self.new_storage(StorageKind.TEMPORARY, value_type)

    def new_expansion_storage(self, value_type: TargetScalarType) -> StorageRef:
        return self.new_storage(StorageKind.EXPANSION, value_type)

    def new_capture(self, value_type: TargetScalarType) -> StorageRef:
        return self.new_storage(StorageKind.CAPTURE, value_type)

    def new_return_storage(self, value_type: TargetScalarType) -> StorageRef:
        return self.new_storage(StorageKind.RETURN, value_type)

    def new_label(self) -> LabelRef:
        self._label_count += 1
        return LabelRef(self._label_count)

    def reserve_storage(self, storage: StorageRef) -> None:
        """Reserve an existing identity before cloning from another allocator."""
        if not isinstance(storage, StorageRef):
            raise CodegenError("IR-STORAGE-KIND", "reserve_storage requires a StorageRef.")
        self._storage_counts[storage.kind] = max(self._storage_counts[storage.kind], storage.storage_id)

    def reserve_label(self, label: LabelRef) -> None:
        """Reserve an existing label identity before cloning a fragment."""
        if not isinstance(label, LabelRef):
            raise CodegenError("IR-LABEL", "reserve_label requires a LabelRef.")
        self._label_count = max(self._label_count, label.label_id)

    @staticmethod
    def storage_name(storage: StorageRef) -> str:
        if not isinstance(storage, StorageRef):
            raise CodegenError("IR-STORAGE-KIND", "storage_name requires a StorageRef.")
        try:
            prefix = FreshNameAllocator._PREFIXES[storage.kind]
        except KeyError as exc:
            raise CodegenError("IR-STORAGE-KIND", f"No identifier prefix for {storage.kind!r}.") from exc
        return f"{prefix}_{storage.storage_id}"

    @staticmethod
    def label_name(label: LabelRef) -> str:
        if not isinstance(label, LabelRef):
            raise CodegenError("IR-LABEL", "label_name requires a LabelRef.")
        return f"spl_lbl_{label.label_id}"


def _map_operand(
    operand: Operand,
    symbol_remap: Mapping[int, StorageLocation],
    storage_remap: Mapping[StorageRef, StorageRef],
) -> Operand:
    if isinstance(operand, NumberLiteral):
        return operand
    if isinstance(operand, StorageRef):
        return storage_remap.get(operand, operand)
    if isinstance(operand, SymbolRef):
        return symbol_remap.get(operand.symbol_id, operand)
    raise CodegenError("IR-OPERAND", f"Unsupported operand {operand!r}.")


def clone_fragment(
    fragment: IRFragment,
    allocator: FreshNameAllocator,
    *,
    symbol_remap: Mapping[int, StorageLocation] | None = None,
    storage_remap: Mapping[StorageRef, StorageRef] | None = None,
    label_remap: Mapping[LabelRef, LabelRef] | None = None,
) -> IRFragment:
    """Clone a fragment using fresh local storage/labels and structural remaps.

    Caller-owned storage and continuation labels are preserved unless an
    explicit mapping is provided. String and comment text is data and is never
    searched or rewritten.
    """
    if not isinstance(fragment, IRFragment) or not isinstance(allocator, FreshNameAllocator):
        raise CodegenError("IR-CLONE", "clone_fragment requires an IRFragment and allocator.")
    symbols = dict(symbol_remap or {})
    storages = dict(storage_remap or {})
    labels = dict(label_remap or {})
    for symbol_id, replacement in symbols.items():
        _positive(symbol_id, "symbol remap key")
        if not isinstance(replacement, (SymbolRef, StorageRef)):
            raise CodegenError("IR-CLONE-SYMBOL", "A symbol remap must target storage, not a literal.")
    for original, replacement in storages.items():
        if not isinstance(original, StorageRef) or not isinstance(replacement, StorageRef):
            raise CodegenError("IR-CLONE-STORAGE", "Storage remaps must map StorageRefs to StorageRefs.")
        if original.value_type is not replacement.value_type:
            raise CodegenError("IR-CLONE-STORAGE-TYPE", "Storage remapping cannot change scalar type.")
    for original, replacement in labels.items():
        if not isinstance(original, LabelRef) or not isinstance(replacement, LabelRef):
            raise CodegenError("IR-CLONE-LABEL", "Label remaps must map LabelRefs to LabelRefs.")

    # Explicit remap targets must also be reserved. Otherwise a later fresh
    # allocation could alias a caller-provided destination not present in this
    # fragment's original identities.
    for replacement in storages.values():
        allocator.reserve_storage(replacement)
    for replacement in symbols.values():
        if isinstance(replacement, StorageRef):
            allocator.reserve_storage(replacement)
    for replacement in labels.values():
        allocator.reserve_label(replacement)

    # Identities may originate from a different allocator. Reserve every source
    # identity before allocating clones so the cloned locals cannot alias any
    # caller-owned storage or continuation label.
    for storage in fragment.declarations:
        allocator.reserve_storage(storage)
    for storage in iter_storage_refs(fragment.instructions):
        allocator.reserve_storage(storage)
    for instruction in fragment.instructions:
        if isinstance(instruction, Label):
            allocator.reserve_label(instruction.label)
        for used_label in _label_uses(instruction):
            allocator.reserve_label(used_label)

    for storage in fragment.declarations:
        if storage not in storages:
            storages[storage] = allocator.new_storage(storage.kind, storage.value_type)
    defined_labels = [instruction.label for instruction in fragment.instructions if isinstance(instruction, Label)]
    if len(defined_labels) != len(set(defined_labels)):
        raise CodegenError("IR-DUPLICATE-LABEL", "Cannot clone a fragment with duplicate labels.")
    for label in defined_labels:
        if label not in labels:
            labels[label] = allocator.new_label()

    def remap_label(label: LabelRef) -> LabelRef:
        return labels.get(label, label)

    def remap_instruction(instruction: Instruction) -> Instruction:
        operand = lambda value: _map_operand(value, symbols, storages)
        if isinstance(instruction, Assign):
            return Assign(operand(instruction.target), operand(instruction.value))  # type: ignore[arg-type]
        if isinstance(instruction, BinaryAssign):
            return BinaryAssign(
                operand(instruction.target), instruction.operator, operand(instruction.left), operand(instruction.right)
            )  # type: ignore[arg-type]
        if isinstance(instruction, UnaryAssign):
            return UnaryAssign(operand(instruction.target), instruction.operator, operand(instruction.value))  # type: ignore[arg-type]
        if isinstance(instruction, PrintNumber):
            return PrintNumber(operand(instruction.value))
        if isinstance(instruction, PrintString):
            return instruction
        if isinstance(instruction, Nop):
            return instruction
        if isinstance(instruction, Comment):
            return instruction
        if isinstance(instruction, Label):
            return Label(remap_label(instruction.label))
        if isinstance(instruction, Jump):
            return Jump(remap_label(instruction.target))
        if isinstance(instruction, ConditionalJump):
            return ConditionalJump(
                operand(instruction.left), instruction.operator, operand(instruction.right),
                remap_label(instruction.true_target), remap_label(instruction.false_target),
            )
        raise CodegenError("IR-INSTRUCTION", f"Cannot clone instruction {instruction!r}.")

    declarations = tuple(storages[storage] for storage in fragment.declarations)
    cloned = IRFragment(declarations, tuple(remap_instruction(item) for item in fragment.instructions))
    _validate_fragment_labels(cloned, allow_external=True)
    return cloned


def _validate_fragment_labels(fragment: IRFragment, *, allow_external: bool) -> None:
    definitions: set[LabelRef] = set()
    uses: set[LabelRef] = set()
    for instruction in fragment.instructions:
        if isinstance(instruction, Label):
            if instruction.label in definitions:
                raise CodegenError("IR-DUPLICATE-LABEL", f"Label {instruction.label.label_id} is defined more than once.")
            definitions.add(instruction.label)
        uses.update(_label_uses(instruction))
    if not allow_external:
        dangling = uses - definitions
        if dangling:
            labels = ", ".join(str(label.label_id) for label in sorted(dangling, key=lambda item: item.label_id))
            raise CodegenError("IR-UNKNOWN-LABEL", f"Jump target(s) not defined: {labels}.")


def iter_storage_refs(instructions: Iterable[Instruction]) -> Iterable[StorageRef]:
    """Yield storage operands in instruction order (useful to integration tools)."""
    for instruction in instructions:
        for operand in _target_operands(instruction):
            if isinstance(operand, StorageRef):
                yield operand
