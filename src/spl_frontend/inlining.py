"""Executable call expansion using the merged immutable code-mine API."""
from __future__ import annotations

from dataclasses import replace

from spl_frontend.call_expansion import TemplateCallEmitter
from spl_frontend.codegen import CodeGenerator, CodegenContext, generate_target
from spl_frontend.codegen_ir import CodegenError, SymbolRef, TargetProgram
from spl_frontend.expansion_environment import ExpansionEnvironment
from spl_frontend.function_templates import prepare_function_templates
from spl_frontend.semantic_model import CheckedProgram, SymbolKind


MAX_EXPANDED_INSTRUCTIONS = 1_000_000


class Inliner(TemplateCallEmitter):
    """Per-compilation call hook, with reusable templates and one allocator."""

    def __init__(self, checked: CheckedProgram, *, context: CodegenContext | None = None) -> None:
        generator = CodeGenerator(checked, context=context)
        self.prepared = prepare_function_templates(checked, context=generator.context)
        super().__init__(generator, self.prepared.templates,
                         max_instructions=MAX_EXPANDED_INSTRUCTIONS)
        generator.call_emitter = self

    def root_environment(self) -> ExpansionEnvironment:
        roots = [s for s in self.resolved.scopes.values() if s.parent_id is None]
        if len(roots) != 1:
            raise CodegenError("GEN-ROOT-SCOPE", "Expected one root lexical scope.")
        root = roots[0]
        return ExpansionEnvironment(root.scope_id, {
            s.symbol_id: SymbolRef(s.symbol_id) for s in self.resolved.symbols.values()
            if s.scope_id == root.scope_id and s.kind is not SymbolKind.FUNCTION
        })


def generate_program(checked: CheckedProgram) -> TargetProgram:
    """Generate a closed program with static calls and inactive code mines.

    D02 uses formal = captured actual. D04's matching arity, left-to-right
    actual evaluation and short-circuit rules remain explicit proposals.
    Generating source requires no installed target compiler.
    """
    inliner = Inliner(checked)
    program = generate_target(checked, call_emitter=inliner, context=inliner.context)
    inliner._check_budget(program.fragment, checked.resolved.tree.root.node_id)
    return replace(program, code_mine=inliner.prepared.code_mine)
