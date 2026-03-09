"""
Minimal formal system over Gödel numbering: axioms = truth-base statements (as Gödel numbers),
optional meaning-extraction rule, and consistency analysis (no two axioms with conflicting meanings).

Formulas are natural numbers (Gödel numbers of Statements, and optionally MeaningStructs).
We do not prove completeness or incompleteness; we only define the system and check consistency.
"""
from pathlib import Path
from typing import Optional

from .godel import encode_statement, decode_statement, encode_meaning, decode_meaning
from .truth_base import load_truth_base, Statement
from .language import conflict, parse_to_meaning


def load_axioms(truth_base_path: str | Path) -> set[int]:
    """Load truth base and return the set of Gödel numbers of each statement (axioms)."""
    statements = load_truth_base(truth_base_path)
    return {encode_statement(s) for s in statements}


def get_theorems(
    axioms: set[int],
    include_meaning_derivations: bool = True,
) -> set[int]:
    """
    Return axioms union (if include_meaning_derivations) Gödel numbers of meaning structs
    for each statement that has a meaning. Decoding failures (e.g. invalid number) are skipped.
    """
    out = set(axioms)
    if not include_meaning_derivations:
        return out
    for n in axioms:
        try:
            st = decode_statement(n)
        except (ValueError, TypeError):
            continue
        if getattr(st, "meaning", None) and isinstance(st.meaning, dict):
            try:
                out.add(encode_meaning(st.meaning))
            except (ValueError, TypeError):
                continue
    return out


def _axiom_meanings(axioms: set[int]) -> list[tuple[int, Optional[dict]]]:
    """Decode each axiom to Statement; return list of (godel_number, meaning_or_none). Meaning from statement.meaning or parse_to_meaning(text)."""
    result: list[tuple[int, Optional[dict]]] = []
    for n in axioms:
        try:
            st = decode_statement(n)
        except (ValueError, TypeError):
            result.append((n, None))
            continue
        meaning = getattr(st, "meaning", None)
        if meaning is None or not isinstance(meaning, dict):
            parsed = parse_to_meaning(getattr(st, "text", "") or "")
            meaning = parsed[0] if parsed else None
        result.append((n, meaning))
    return result


def is_consistent(axioms: set[int]) -> bool:
    """Return True iff no two axioms have conflicting meanings. Pairs with missing meaning are not considered conflicting."""
    pairs = conflicting_pairs(axioms)
    return len(pairs) == 0


def conflicting_pairs(axioms: set[int]) -> list[tuple[int, int]]:
    """Return list of (n, m) axiom pairs (Gödel numbers) whose meanings conflict."""
    decoded = _axiom_meanings(axioms)
    result: list[tuple[int, int]] = []
    for i, (n, mean_i) in enumerate(decoded):
        if mean_i is None:
            continue
        for j, (m, mean_j) in enumerate(decoded):
            if i >= j or mean_j is None:
                continue
            if conflict(mean_i, mean_j):
                result.append((n, m))
    return result


def check_consistency_of_paths(
    truth_base_path: Optional[str | Path] = None,
    ir_path: Optional[str | Path] = None,
    ir_limit: Optional[int] = None,
) -> tuple[bool, list[tuple[int, int]]]:
    """
    Load axioms from truth base and/or IR, run consistency check.
    Returns (is_consistent, list of conflicting (godel_id, godel_id) pairs).
    """
    axioms: set[int] = set()
    if truth_base_path and Path(truth_base_path).exists():
        axioms |= load_axioms(truth_base_path)
    if ir_path and Path(ir_path).exists():
        try:
            from .ir_bridge import load_axioms_from_ir
            axioms |= load_axioms_from_ir(ir_path, limit=ir_limit)
        except Exception:
            pass
    pairs = conflicting_pairs(axioms)
    return (len(pairs) == 0, pairs)
