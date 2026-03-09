"""
Bridge from dictionary/ingestion IR (JSONL: subject, definition, relations, examples)
to scratchLLM truth-base Statements and Gödel axioms.

Use load_ir_jsonl(path) to get Statements, or load_axioms_from_ir(path) to get
Gödel numbers of those statements for use with the formal system (is_consistent, etc.).
"""
import json
from pathlib import Path
from typing import Any

from .truth_base import Statement
from .godel import encode_statement


# Tier for IR-derived statements (contingent / dictionary)
IR_TIER = 2
IR_SOURCE = "dictionary_ir"

# Keep statement text short so Gödel encoding stays tractable (decode is slow for huge numbers).
MAX_TEXT_LENGTH = 280


def _relation_to_meaning(rel: dict[str, Any]) -> dict[str, Any] | None:
    """Convert one IR relation {source, relation, target} to a MeaningStruct (BE or PRED)."""
    source = (rel.get("source") or "").strip()
    relation = (rel.get("relation") or "").strip()
    target = (rel.get("target") or "").strip()
    if not source or not relation:
        return None
    if not target and relation != "is_a":
        return None
    if relation == "is_a":
        return {"type": "BE", "subj": source, "obj": target or ""}
    return {"type": "PRED", "subj": source, "pred": relation, "obj": target}


def ir_record_to_statement(record: dict[str, Any]) -> Statement:
    """
    Convert one IR record (subject, definition?, relations?, examples?) to a Statement.
    Meaning is taken from the first relation: is_a -> BE(subj, obj); else -> PRED(subj, pred, obj).
    """
    subject = (record.get("subject") or "").strip()
    definition = (record.get("definition") or "").strip()
    relations = record.get("relations")
    if isinstance(relations, list) and len(relations) > 0:
        first = relations[0]
        if isinstance(first, dict):
            meaning = _relation_to_meaning(first)
        else:
            meaning = None
    else:
        meaning = None

    text = definition if definition else f"{subject} (no definition)"
    if not text.strip():
        text = subject or "(empty)"
    if len(text) > MAX_TEXT_LENGTH:
        text = text[: MAX_TEXT_LENGTH - 3] + "..."

    return Statement(
        text=text,
        tier=IR_TIER,
        source=IR_SOURCE,
        category="ir",
        id=subject or None,
        meaning=meaning,
    )


def load_ir_jsonl(path: str | Path, limit: int | None = None) -> list[Statement]:
    """Load an IR JSONL file and return a list of Statements (one per line). If limit is set, only first limit lines."""
    path = Path(path)
    if not path.exists():
        return []
    statements: list[Statement] = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit is not None and i >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            statements.append(ir_record_to_statement(record))
    return statements


def load_axioms_from_ir(ir_path: str | Path, limit: int | None = None) -> set[int]:
    """Load IR JSONL, convert each record to a Statement, return set of Gödel numbers (axioms). If limit is set, only first limit lines."""
    statements = load_ir_jsonl(ir_path, limit=limit)
    return {encode_statement(s) for s in statements}
