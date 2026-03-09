"""Tests for formal-only response (no model)."""
import json
import tempfile
from pathlib import Path

import pytest

from base.respond import respond_formal_only
from base.truth_base import Statement, save_truth_base


def test_respond_formal_only_truth_base():
    """With a tiny truth base, response is non-empty and used_godel_ids returned."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        save_truth_base(
            [
                Statement("Recursion is a function that calls itself.", 2, "curated"),
                Statement("A base case stops the recursion.", 2, "curated"),
            ],
            f.name,
        )
        path = f.name
    try:
        response, used_ids, _ = respond_formal_only(
            "What is recursion?",
            truth_base_path=path,
            top_k=3,
            resolve=True,
        )
        assert isinstance(response, str)
        assert "recursion" in response.lower() or "function" in response.lower()
        assert isinstance(used_ids, list)
        assert len(used_ids) >= 1
    finally:
        Path(path).unlink(missing_ok=True)


def test_respond_formal_only_ir():
    """With IR JSONL, response contains definition content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "subject": "bytecode",
                    "definition": "Intermediate representation of source code for a virtual machine.",
                    "relations": [{"source": "bytecode", "relation": "is_a", "target": "programming_concept"}],
                }
            )
            + "\n"
        )
        path = f.name
    try:
        response, used_ids, _ = respond_formal_only(
            "What is bytecode?",
            ir_path=path,
            top_k=3,
        )
        assert isinstance(response, str)
        assert "bytecode" in response.lower() or "intermediate" in response.lower()
        assert len(used_ids) >= 1
    finally:
        Path(path).unlink(missing_ok=True)


def test_respond_formal_only_no_data():
    """With no truth base or IR path, returns empty string and empty list."""
    response, used_ids, resolved = respond_formal_only("What is X?", top_k=5)
    assert response == ""
    assert used_ids == []
    assert resolved == []


def test_respond_formal_only_nonexistent_paths():
    """With only nonexistent paths, returns empty (no exception)."""
    response, used_ids, _ = respond_formal_only(
        "What is Y?",
        truth_base_path=Path("/nonexistent/truth.jsonl"),
        ir_path=Path("/nonexistent/ir.jsonl"),
    )
    assert response == ""
    assert used_ids == []


def test_respond_formal_only_returns_godel_ids():
    """Used Gödel IDs are positive integers for each resolved statement."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        save_truth_base([Statement("2+2 equals 4.", 0, "curated")], f.name)
        path = f.name
    try:
        _, used_ids, _ = respond_formal_only("What is 2+2?", truth_base_path=path, top_k=1)
        assert len(used_ids) <= 1
        for n in used_ids:
            assert isinstance(n, int)
            assert n >= 1
    finally:
        Path(path).unlink(missing_ok=True)
