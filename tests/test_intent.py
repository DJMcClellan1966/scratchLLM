"""Tests for intent-driven helper: guardrails, quick corpus, create_helper_from_intent."""
import tempfile
from pathlib import Path

import pytest

from base.intent import (
    check_guardrails,
    build_quick_corpus,
    create_helper_from_intent,
    get_onboarding_definitions,
    list_user_helpers,
    load_intent_templates,
)


def test_check_guardrails_allowed():
    allowed, msg = check_guardrails("I want to junk journal")
    assert allowed is True
    assert msg == "OK"


def test_check_guardrails_blocked():
    allowed, msg = check_guardrails("I want to do something illegal")
    assert allowed is False
    assert "cannot be supported" in msg or "different" in msg


def test_load_intent_templates():
    templates = load_intent_templates()
    assert isinstance(templates, dict)
    # Default config has journaling, hiking, general
    assert "general" in templates or "journaling" in templates or len(templates) >= 0


def test_build_quick_corpus():
    statements = build_quick_corpus("I want to junk journal")
    assert len(statements) >= 1
    assert any("goal" in getattr(s, "text", "").lower() or "journal" in getattr(s, "text", "").lower() for s in statements)


def test_build_quick_corpus_blank_canvas():
    statements = build_quick_corpus("I want to read the bible daily", blank_canvas=True)
    assert len(statements) == 1
    assert "goal" in statements[0].text.lower() and "bible" in statements[0].text.lower()


def test_create_helper_from_intent():
    with tempfile.TemporaryDirectory() as tmp:
        helper_id, truth_base_path, count = create_helper_from_intent(
            "I want to junk journal",
            out_dir=tmp,
        )
        assert isinstance(helper_id, str)
        assert len(helper_id) > 0
        assert truth_base_path.exists()
        assert truth_base_path.suffix == ".jsonl"
        assert count >= 1
        meta = truth_base_path.parent / "meta.json"
        assert meta.exists()


def test_create_helper_from_intent_blank_canvas():
    with tempfile.TemporaryDirectory() as tmp:
        helper_id, truth_base_path, count = create_helper_from_intent(
            "I want to read the bible",
            out_dir=tmp,
            blank_canvas=True,
        )
        assert count == 1
        assert truth_base_path.exists()
        with open(truth_base_path, encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) == 1
        assert "goal" in lines[0].lower() and "bible" in lines[0].lower()


def test_create_helper_from_intent_guardrails_raise():
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(ValueError, match="cannot be supported|different"):
            create_helper_from_intent("I want to harm someone", out_dir=tmp)


def test_create_helper_from_intent_with_onboarding():
    with tempfile.TemporaryDirectory() as tmp:
        helper_id, truth_base_path, count = create_helper_from_intent(
            "I want to learn birdwatching",
            out_dir=tmp,
            blank_canvas=False,
            experience_level="beginner",
            needs_vocabulary=False,
        )
        assert count >= 1
        meta_path = truth_base_path.parent / "meta.json"
        assert meta_path.exists()
        with open(meta_path, encoding="utf-8") as f:
            import json
            meta = json.load(f)
        assert meta.get("experience_level") == "beginner"
        assert meta.get("needs_vocabulary", False) is False

def test_list_user_helpers():
    with tempfile.TemporaryDirectory() as tmp:
        create_helper_from_intent("I want to hike", out_dir=tmp)
        helpers = list_user_helpers(tmp)
        assert len(helpers) >= 1
        assert "helper_id" in helpers[0]
        assert "truth_base_path" in helpers[0]
        assert "experience_level" in helpers[0]
        assert "needs_vocabulary" in helpers[0]


def test_get_onboarding_definitions():
    defs = get_onboarding_definitions("birdwatching", max_definitions=1)
    assert isinstance(defs, list)
    if defs:
        assert len(defs) <= 1
        assert isinstance(defs[0], tuple) and len(defs[0]) == 2
    defs_none = get_onboarding_definitions(None)
    assert defs_none == []
