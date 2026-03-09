"""Tests for the minimal formal system (axioms, theorems, consistency)."""
import tempfile
from pathlib import Path

import pytest

from base.formal_system import load_axioms, get_theorems, is_consistent, conflicting_pairs, check_consistency_of_paths
from base.godel import decode_statement, encode_meaning
from base.truth_base import Statement, save_truth_base
from base.language import conflict


def test_load_axioms_from_temp_truth_base():
    """load_axioms from a temp truth-base JSONL returns set of ints; each decodes to Statement; size matches."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "tb.jsonl"
        sts = [
            Statement("2+2=4", 0, "curated"),
            Statement("Earth orbits Sun.", 1, "curated"),
        ]
        save_truth_base(sts, path)
        axioms = load_axioms(path)
        assert isinstance(axioms, set)
        assert len(axioms) == 2
        for n in axioms:
            assert isinstance(n, int)
            assert n >= 1
            st = decode_statement(n)
            assert isinstance(st, Statement)
            assert st.text in ("2+2=4", "Earth orbits Sun.")


def test_get_theorems_includes_axioms():
    """get_theorems returns at least the axioms."""
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "t.jsonl"
        save_truth_base([Statement("x is 1", 0)], p)
        axioms = load_axioms(p)
    theorems = get_theorems(axioms, include_meaning_derivations=False)
    assert theorems == axioms
    theorems2 = get_theorems(axioms, include_meaning_derivations=True)
    assert axioms <= theorems2


def test_get_theorems_meaning_derivations():
    """With include_meaning_derivations=True, theorems include meaning Gödel number when statement has meaning."""
    meaning = {"type": "BE", "subj": "2+2", "obj": "4"}
    st = Statement("2+2=4", 0, "curated", meaning=meaning)
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "t.jsonl"
        save_truth_base([st], p)
        axioms = load_axioms(p)
    theorems = get_theorems(axioms, include_meaning_derivations=True)
    assert len(axioms) == 1
    assert len(theorems) >= 1
    meaning_godel = encode_meaning(meaning)
    assert meaning_godel in theorems


def test_is_consistent_no_conflicts():
    """Axiom set with no conflicting meanings -> is_consistent True."""
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "t.jsonl"
        save_truth_base(
            [
                Statement("2+2=4", 0),
                Statement("Earth orbits Sun.", 1),
            ],
            p,
        )
        axioms = load_axioms(p)
    assert is_consistent(axioms) is True
    assert conflicting_pairs(axioms) == []


def test_is_consistent_with_conflicts():
    """Axiom set where two statements conflict (same subj, different obj) -> is_consistent False."""
    st1 = Statement("x is 1", 0, meaning={"type": "BE", "subj": "x", "obj": "1"})
    st2 = Statement("x is 2", 0, meaning={"type": "BE", "subj": "x", "obj": "2"})
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "t.jsonl"
        save_truth_base([st1, st2], p)
        axioms = load_axioms(p)
    assert is_consistent(axioms) is False
    pairs = conflicting_pairs(axioms)
    assert len(pairs) >= 1
    for n, m in pairs:
        s1 = decode_statement(n)
        s2 = decode_statement(m)
        mean1 = s1.meaning or {}
        mean2 = s2.meaning or {}
        assert conflict(mean1, mean2)


def test_check_consistency_of_paths():
    """check_consistency_of_paths with truth_base returns (consistent, pairs)."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "tb.jsonl"
        save_truth_base([Statement("A is B", 0, "curated")], path)
        consistent, pairs = check_consistency_of_paths(truth_base_path=path)
        assert consistent is True
        assert pairs == []
        save_truth_base([
            Statement("x is 1", 0, meaning={"type": "BE", "subj": "x", "obj": "1"}),
            Statement("x is 2", 0, meaning={"type": "BE", "subj": "x", "obj": "2"}),
        ], path)
        consistent2, pairs2 = check_consistency_of_paths(truth_base_path=path)
        assert consistent2 is False
        assert len(pairs2) >= 1


def test_save_truth_base_check_consistency_raises():
    """save_truth_base(..., check_consistency=True) raises ValueError when statements are inconsistent."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "tb.jsonl"
        inconsistent = [
            Statement("x is 1", 0, meaning={"type": "BE", "subj": "x", "obj": "1"}),
            Statement("x is 2", 0, meaning={"type": "BE", "subj": "x", "obj": "2"}),
        ]
        with pytest.raises(ValueError, match="inconsistent"):
            save_truth_base(inconsistent, path, check_consistency=True)
        # Without check, save succeeds
        save_truth_base(inconsistent, path, check_consistency=False)
        assert path.exists()
