"""Lexical declaration identities mapped to one static inline instance.

No spelling lookup takes place here. A child capture resolves through the
current parent's environment, so a second parent call never reuses old storage.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from spl_frontend.codegen_ir import CodegenError, StorageLocation, StorageRef, SymbolRef


@dataclass(frozen=True, slots=True)
class ExpansionEnvironment(Mapping[int, StorageLocation]):
    scope_id: int
    storage_by_symbol: Mapping[int, StorageLocation] = field(default_factory=dict)
    parent: ExpansionEnvironment | None = None

    def __post_init__(self) -> None:
        if type(self.scope_id) is not int or self.scope_id < 1:
            raise ValueError("Expansion scope must be a positive integer.")
        values = dict(self.storage_by_symbol)
        if any(type(key) is not int or key < 1 or not isinstance(value, (StorageRef, SymbolRef))
               for key, value in values.items()):
            raise ValueError("Expansion bindings require symbol IDs and Storage values.")
        if self.parent is not None and not isinstance(self.parent, ExpansionEnvironment):
            raise ValueError("Expansion parent must be an ExpansionEnvironment.")
        object.__setattr__(self, "storage_by_symbol", MappingProxyType(values))

    def resolve(self, symbol_id: int) -> StorageLocation:
        if type(symbol_id) is not int or symbol_id < 1:
            raise ValueError("Symbol ID must be a positive integer.")
        environment: ExpansionEnvironment | None = self
        seen: set[int] = set()
        while environment is not None:
            if id(environment) in seen:
                raise CodegenError("GEN-ENV-CYCLE", "Cyclic expansion environment.")
            seen.add(id(environment))
            if symbol_id in environment.storage_by_symbol:
                return environment.storage_by_symbol[symbol_id]
            environment = environment.parent
        raise CodegenError("GEN-UNBOUND-CAPTURE", f"No instantiated storage for symbol {symbol_id}.")

    def __getitem__(self, symbol_id: int) -> StorageLocation:
        try:
            return self.resolve(symbol_id)
        except CodegenError as exc:
            if exc.code == "GEN-UNBOUND-CAPTURE":
                raise KeyError(symbol_id) from exc
            raise

    def __iter__(self) -> Iterator[int]:
        seen_ids = set()
        seen_envs = set()
        env = self
        while env is not None:
            if id(env) in seen_envs:
                raise CodegenError("GEN-ENV-CYCLE", "Cyclic expansion environment.")
            seen_envs.add(id(env))
            for symbol_id in env.storage_by_symbol:
                if symbol_id not in seen_ids:
                    seen_ids.add(symbol_id)
                    yield symbol_id
            env = env.parent

    def __len__(self) -> int:
        return sum(1 for _ in self)
