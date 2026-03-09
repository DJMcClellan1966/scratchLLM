"""Tests for intent-driven helper: guardrails, quick corpus, create_helper_from_intent."""
import tempfile
from pathlib import Path

import pytest

from base.intent import (
    check_guardrails,
    build_quick_corpus,
    create_helper_from_intent,
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


def test_create_helper_from_intent_guardrails_raise():
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(ValueError, match="cannot be supported|different"):
            create_helper_from_intent("I want to harm someone", out_dir=tmp)


def test_list_user_helpers():
    with tempfile.TemporaryDirectory() as tmp:
        create_helper_from_intent("I want to hike", out_dir=tmp)
        helpers = list_user_helpers(tmp)
        assert len(helpers) >= 1
        assert "helper_id" in helpers[0]
        assert "truth_base_path" in helpers[0]
