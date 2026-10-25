"""Create reproducible one-rule semantic faults without damaging SPL syntax.

Mutations use parser leaves, so strings and comments are never substring
matches. A valid baseline is required. None means the requested isolated fault
cannot be applied (for example decimal+mod to a program already containing div).
"""
from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal

from spl_frontend.lexer import tokenize
from spl_frontend.parser import parse
from spl_frontend.source import SourceFile
from spl_frontend.tree import SyntaxTree
from spl_frontend.tree_walkers import iter_leaves
from spl_frontend.name_analysis import resolve_names
from spl_frontend.type_analysis import check_types

MutationType = Literal["name_undeclared", "name_duplicate", "type_void_in_term",
                       "type_num_as_instr", "numeric_mod_div", "numeric_decimal_mod"]

@dataclass(frozen=True)
class TokenEdit:
    index: int
    removed: tuple[str, ...]
    inserted: tuple[str, ...]


@dataclass(frozen=True)
class Mutation:
    original_source: str
    mutated_source: str
    mutation_type: MutationType
    expected_phase: str
    expected_code: str
    description: str
    seed: int
    edits: tuple[TokenEdit, ...] = ()


def generate_mutation(source: str, mutation_type: MutationType | None = None,
                      seed: int = 0) -> Mutation | None:
    tree = SyntaxTree()
    path = Path("mutation.spl")
    parse(tokenize(SourceFile(path, source)), tree, path)
    check_types(resolve_names(tree, path=path))
    leaves = list(iter_leaves(tree))
    words = [leaf.contents for leaf in leaves]
    positions = {leaf.node_id: i for i, leaf in enumerate(leaves)}
    assert tree.root is not None
    root_p = tree.get_node(tree.root.child_ids[0])
    colon1 = positions[root_p.child_ids[1]]
    colon2 = positions[root_p.child_ids[3]]
    fresh = "#fault"
    while fresh in words:
        fresh += "0"
    choices: list[MutationType] = ["name_undeclared", "name_duplicate", "type_void_in_term",
                                   "type_num_as_instr", "numeric_mod_div", "numeric_decimal_mod"]
    if mutation_type is None:
        random.Random(seed).shuffle(choices)
    elif mutation_type not in choices:
        raise ValueError(f"Unknown mutation type: {mutation_type}")
    else:
        choices = [mutation_type]
    for kind in choices:
        result = list(words)
        phase = "type_analysis"
        if kind == "name_undeclared":
            result.extend([fresh, "=", "0", ";"])
            code, phase = "NAME-UNDECLARED-VARIABLE", "name_analysis"
        elif kind == "name_duplicate":
            result[colon1:colon1] = [fresh, fresh]
            code, phase = "NAME-DUPLICATE-VARIABLE", "name_analysis"
        elif kind == "type_void_in_term":
            result[colon2:colon2] = ["void", fresh, "(", ")", "{", ":", ":", "return", "}"]
            result.extend(["print", "(", fresh, "(", ")", ")", ";"])
            code = "TYPE-TERM-CALL"
        elif kind == "type_num_as_instr":
            result[colon2:colon2] = ["num", fresh, "(", ")", "{", ":", ":", "return", "(", "0", ")", "}"]
            result.extend([fresh, "(", ")", ";"])
            code = "TYPE-INSTR-CALL"
        elif kind == "numeric_mod_div":
            # Avoid adding a second independent decimal/mod violation.
            if any("." in w and w.lstrip("-")[:1].isdigit() for w in words):
                continue
            result.extend("print ( add ( mod ( 5 2 ) div ( 4 2 ) ) ) ;".split())
            code = "FLOAT-INT-CONFLICT"
        else:
            if "div" in words:
                continue
            result.extend("print ( mod ( 5.5 2 ) ) ;".split())
            code = "DECIMAL-WITH-MOD"
        edits = tuple(TokenEdit(i, tuple(words[i:j]), tuple(result[k:l]))
                      for tag, i, j, k, l in SequenceMatcher(a=words, b=result, autojunk=False).get_opcodes()
                      if tag != "equal")
        return Mutation(source, " ".join(result) + " ", kind, phase, code,
                        f"Insert an isolated {kind} fault into a valid program", seed, edits)
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--type", choices=MutationType.__args__)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    mutation = generate_mutation(args.source.read_text(encoding="utf-8"), args.type, args.seed)
    if mutation is None:
        parser.error("requested isolated mutation is not applicable")
    print(mutation.mutated_source, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
