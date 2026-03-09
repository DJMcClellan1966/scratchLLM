"""Tests for IR bridge: IR records -> Statements -> Gödel axioms."""
import json
import tempfile
from pathlib import Path

import pytest

from base.ir_bridge import ir_record_to_statement, load_ir_jsonl, load_axioms_from_ir
from base.truth_base import Statement
from base.formal_system import is_consistent, conflicting_pairs
from base.godel import decode_statement, encode_statement


def test_ir_record_to_statement_is_a():
    """is_a relation -> BE meaning."""
    record = {
        "subject": "antelope",
        "definition": "A large hoofed mammal.",
        "relations": [{"source": "antelope", "relation": "is_a", "target": "mammal"}],
        "examples": ["Gazelle"],
    }
    st = ir_record_to_statement(record)
    assert isinstance(st, Statement)
    assert st.text == "A large hoofed mammal."
    assert st.tier == 2
    assert st.source == "dictionary_ir"
    assert st.meaning is not None
    assert st.meaning["type"] == "BE"
    assert st.meaning["subj"] == "antelope"
    assert st.meaning["obj"] == "mammal"


def test_ir_record_to_statement_pred():
    """Non-is_a relation -> PRED meaning."""
    record = {
        "subject": "pierce",
        "definition": "To cut through.",
        "relations": [{"source": "pierce", "relation": "enables", "target": "cutting"}],
    }
    st = ir_record_to_statement(record)
    assert st.meaning is not None
    assert st.meaning["type"] == "PRED"
    assert st.meaning["subj"] == "pierce"
    assert st.meaning["pred"] == "enables"
    assert st.meaning["obj"] == "cutting"


def test_ir_record_to_statement_no_relations():
    """No relations -> meaning None, text from definition or subject."""
    record = {"subject": "foo", "definition": ""}
    st = ir_record_to_statement(record)
    assert st.meaning is None
    assert "foo" in st.text

    record2 = {"subject": "bar", "definition": "Bar is something."}
    st2 = ir_record_to_statement(record2)
    assert st2.meaning is None
    assert st2.text == "Bar is something."


def test_load_ir_jsonl():
    """Load IR JSONL from temp file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write(json.dumps({"subject": "a", "definition": "Def a", "relations": [{"source": "a", "relation": "is_a", "target": "concept"}]}) + "\n")
        f.write(json.dumps({"subject": "b", "definition": "Def b", "relations": [{"source": "b", "relation": "causes", "target": "effect"}]}) + "\n")
        path = f.name
    try:
        statements = load_ir_jsonl(path)
        assert len(statements) == 2
        assert statements[0].meaning["type"] == "BE"
        assert statements[1].meaning["type"] == "PRED"
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_ir_jsonl_nonexistent():
    """Nonexistent path -> empty list."""
    assert load_ir_jsonl(Path("/nonexistent/pregenerated_ir.jsonl")) == []


def test_load_axioms_from_ir():
    """load_axioms_from_ir returns set of ints, each decodes to Statement."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write(json.dumps({"subject": "x", "definition": "X is 1", "relations": [{"source": "x", "relation": "is_a", "target": "one"}]}) + "\n")
        path = f.name
    try:
        axioms = load_axioms_from_ir(path)
        assert isinstance(axioms, set)
        assert len(axioms) == 1
        for n in axioms:
            st = decode_statement(n)
            assert st.text == "X is 1"
            assert st.meaning["subj"] == "x"
            assert st.meaning["obj"] == "one"
    finally:
        Path(path).unlink(missing_ok=True)


def test_godel_roundtrip_ir_statement():
    """IR -> Statement -> encode_statement -> decode_statement -> same content."""
    record = {"subject": "bytecode", "definition": "Intermediate representation.", "relations": [{"source": "bytecode", "relation": "is_a", "target": "programming_concept"}]}
    st = ir_record_to_statement(record)
    n = encode_statement(st)
    back = decode_statement(n)
    assert back.text == st.text
    assert back.tier == st.tier
    assert back.source == st.source
    assert back.meaning == st.meaning


def test_consistency_on_ir_axioms():
    """is_consistent(load_axioms_from_ir(...)) runs; consistent set -> True."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write(json.dumps({"subject": "a", "definition": "A", "relations": [{"source": "a", "relation": "is_a", "target": "alpha"}]}) + "\n")
        f.write(json.dumps({"subject": "b", "definition": "B", "relations": [{"source": "b", "relation": "is_a", "target": "beta"}]}) + "\n")
        path = f.name
    try:
        axioms = load_axioms_from_ir(path)
        assert is_consistent(axioms) is True
        assert conflicting_pairs(axioms) == []
    finally:
        Path(path).unlink(missing_ok=True)


def test_consistency_conflict_ir():
    """Two IR records with same subj/type but different obj -> inconsistent."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write(json.dumps({"subject": "x", "definition": "X is 1", "relations": [{"source": "x", "relation": "is_a", "target": "1"}]}) + "\n")
        f.write(json.dumps({"subject": "x", "definition": "X is 2", "relations": [{"source": "x", "relation": "is_a", "target": "2"}]}) + "\n")
        path = f.name
    try:
        axioms = load_axioms_from_ir(path)
        assert is_consistent(axioms) is False
        pairs = conflicting_pairs(axioms)
        assert len(pairs) >= 1
    finally:
        Path(path).unlink(missing_ok=True)
