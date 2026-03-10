"""Tests for base.learning: append_to_truth_base, statements_from_user_note, statements_from_outcome."""
import tempfile
from pathlib import Path

import pytest

from base.learning import (
    append_to_truth_base,
    statements_from_user_note,
    statements_from_outcome,
)
from base.truth_base import Statement, load_truth_base, save_truth_base


def test_statements_from_user_note():
    stmts = statements_from_user_note("I prefer low water for basil")
    assert len(stmts) == 1
    assert stmts[0].text == "I prefer low water for basil"
    assert stmts[0].tier == 2
    assert stmts[0].source == "user"
    assert stmts[0].category == "user_note"


def test_statements_from_user_note_empty():
    assert statements_from_user_note("") == []
    assert statements_from_user_note("   ") == []


def test_statements_from_outcome():
    stmts = statements_from_outcome("Try basil in east window", "success", "Low water worked")
    assert len(stmts) >= 1
    assert "Experiment:" in stmts[0].text and "Result: success" in stmts[0].text
    assert stmts[0].category == "outcome"
    assert stmts[0].source == "user"


def test_statements_from_outcome_failure_skipped():
    stmts = statements_from_outcome("Brew batch #2", "failure", "")
    assert len(stmts) == 1
    assert "failure" in stmts[0].text.lower()
    stmts2 = statements_from_outcome("Skip this", "skipped", "")
    assert "skipped" in stmts2[0].text.lower()


def test_statements_from_outcome_empty_desc():
    assert statements_from_outcome("", "success", "") == []


def test_append_to_truth_base_new_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tb.jsonl"
        st = Statement("First fact", 2, "user", category="test")
        append_to_truth_base(path, [st])
        loaded = load_truth_base(path)
        assert len(loaded) == 1
        assert loaded[0].text == "First fact"


def test_append_to_truth_base_existing():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tb.jsonl"
        save_truth_base([Statement("Existing", 1, "curated")], path)
        append_to_truth_base(path, statements_from_user_note("New note"))
        loaded = load_truth_base(path)
        assert len(loaded) == 2
        assert loaded[0].text == "Existing"
        assert loaded[1].text == "New note"


def test_append_persists_and_retrieval_sees_it():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tb.jsonl"
        save_truth_base(
            [Statement("Gardening tip: water in morning.", 2, "curated", category="gardening")],
            path,
        )
        append_to_truth_base(path, statements_from_outcome("Basil east window", "success", "Low water"))
        from base import respond_formal_only
        response, used_ids, used_stmts, _ = respond_formal_only(
            "What worked for basil?",
            truth_base_path=path,
            top_k=5,
        )
        texts = [s.text for s in used_stmts]
        assert any("basil" in t.lower() or "water" in t.lower() for t in texts)
