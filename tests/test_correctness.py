"""Tests for correctness: scaling, tokenizer, language, base, model forward."""
import tempfile
from pathlib import Path

import pytest
import torch


def test_scaling_small_corpus():
    from config.scaling import compute_scale
    scale = compute_scale(100, 50, 10)
    assert scale.vocab_size <= 8192
    assert scale.context_len <= 512
    assert scale.d_model in (256, 384, 512, 768)
    assert scale.n_layers >= 2
    assert scale.d_ff == 4 * scale.d_model


def test_scaling_zero_tokens_boundaries():
    """compute_scale(0,0,0) yields vocab_size >= 512, context_len >= 64."""
    from config.scaling import compute_scale
    scale = compute_scale(0, 0, 0)
    assert scale.vocab_size >= 512
    assert scale.context_len >= 64


def test_scaling_large_tokens_caps():
    """Very large n_tokens yields vocab_size <= 8192, context_len <= 512."""
    from config.scaling import compute_scale
    scale = compute_scale(20_000_000, 0, 0)
    assert scale.vocab_size <= 8192
    assert scale.context_len <= 512


def test_scaling_large_corpus():
    from config.scaling import compute_scale
    scale = compute_scale(5_000_000, 0, 1000)
    assert scale.d_model >= 512
    assert scale.n_layers >= 6


def test_language_parse_be():
    from base.language import parse_to_meaning, meaning_to_text
    m = parse_to_meaning("2 + 2 = 4")
    assert len(m) == 1
    assert m[0]["type"] == "BE"
    assert m[0]["subj"] == "2 + 2"
    assert m[0]["obj"] == "4"
    assert "2" in meaning_to_text(m[0]) and "4" in meaning_to_text(m[0])


def test_language_parse_query():
    from base.language import parse_to_meaning, meaning_to_text
    m = parse_to_meaning("What is the capital of France?")
    assert len(m) == 1
    assert m[0]["type"] == "QUERY"
    assert "capital" in m[0]["ref"]
    assert "What" in meaning_to_text(m[0])


def test_language_infer_tier():
    from base.language import parse_to_meaning, infer_tier_from_meaning
    m = parse_to_meaning("2 + 2 = 4")
    assert infer_tier_from_meaning(m[0]) == 0
    m2 = parse_to_meaning("Paris is the capital of France.")
    assert infer_tier_from_meaning(m2[0]) == 2


def test_language_empty_inputs():
    """parse_to_meaning('') returns []; meaning_to_text({}) returns ''; infer_tier_from_meaning({}) returns None."""
    from base.language import parse_to_meaning, meaning_to_text, infer_tier_from_meaning
    assert parse_to_meaning("") == []
    assert meaning_to_text({}) == ""
    assert infer_tier_from_meaning({}) is None


def test_language_pred_pattern():
    """parse_to_meaning handles PRED pattern (e.g. 'Earth revolves around Sun')."""
    from base.language import parse_to_meaning, meaning_to_text, infer_tier_from_meaning
    m = parse_to_meaning("Earth revolves around Sun.")
    assert len(m) >= 1
    assert m[0].get("type") == "PRED"
    assert infer_tier_from_meaning(m[0]) == 2
    out = meaning_to_text(m[0])
    assert "Earth" in out or "Sun" in out


def test_language_conflict():
    from base.language import conflict, resolve_conflicts
    from base.truth_base import Statement
    a = {"type": "BE", "subj": "x", "obj": "1"}
    b = {"type": "BE", "subj": "x", "obj": "2"}
    assert conflict(a, b) is True
    assert conflict(a, a) is False
    # resolve: keep lower tier
    st1, st2 = Statement("x is 1", 0), Statement("x is 2", 5)
    resolved = resolve_conflicts([(st1, a), (st2, b)])
    assert len(resolved) == 1
    assert resolved[0].tier == 0


def test_truth_base_load_save():
    from base.truth_base import Statement, load_truth_base, save_truth_base
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "tb.jsonl"
        sts = [
            Statement("2+2=4", 0),
            Statement("Earth orbits Sun.", 1),
        ]
        save_truth_base(sts, path)
        loaded = load_truth_base(path)
        assert len(loaded) == 2
        assert loaded[0].text == "2+2=4"
        assert loaded[0].tier == 0


def test_truth_base_parse_meaning_if_missing():
    from base.truth_base import Statement, load_truth_base, save_truth_base
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "tb.jsonl"
        save_truth_base([Statement("2 + 2 = 4", 0)], path)
        loaded = load_truth_base(path, parse_meaning_if_missing=True)
        assert len(loaded) == 1
        assert loaded[0].meaning is not None
        assert loaded[0].meaning.get("type") == "BE"


def test_structure_format_context():
    from base.structure import format_context, FormattedContext
    fc = format_context(["fact1"], ["ctx1"], "prompt")
    assert isinstance(fc, FormattedContext)
    assert "[FACT]" in fc.context_string
    assert "[CONTEXT]" in fc.context_string
    assert "[PROMPT]" in fc.context_string
    assert "fact1" in fc.context_string
    assert "prompt" in fc.context_string


def test_structure_format_context_empty():
    """format_context([], [], '') contains [PROMPT]; empty fact/context omit blocks; no crash."""
    from base.structure import format_context, FormattedContext
    fc = format_context([], [], "")
    assert isinstance(fc, FormattedContext)
    assert "[PROMPT]" in fc.context_string


def test_retrieve_word_overlap():
    from base.retrieve import retrieve_truth_base
    base_path = Path(__file__).resolve().parent.parent / "base" / "truth_base.jsonl"
    if base_path.exists():
        r = retrieve_truth_base("earth sun", base_path, top_k=3)
        assert isinstance(r, list)
        assert all(isinstance(x, str) for x in r)


def test_retrieve_for_prompt_use_meaning():
    from base.retrieve import retrieve_for_prompt
    base_path = Path(__file__).resolve().parent.parent / "base" / "truth_base.jsonl"
    if base_path.exists():
        t, c = retrieve_for_prompt("what is 2+2?", truth_base_path=base_path, use_meaning=True)
        assert isinstance(t, list)
        assert isinstance(c, list)


def test_retrieve_truth_base_empty_query_top_k_zero():
    """retrieve_truth_base('', path, top_k=0) returns []."""
    from base.retrieve import retrieve_truth_base
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write('{"text": "x", "tier": 0, "source": "curated"}\n')
        path = Path(f.name)
    try:
        r = retrieve_truth_base("", path, top_k=0)
        assert r == []
    finally:
        path.unlink(missing_ok=True)


def test_retrieve_for_prompt_no_paths():
    """retrieve_for_prompt('x', truth_base_path=None) returns (truth_chunks, corpus_chunks) with empty truth."""
    from base.retrieve import retrieve_for_prompt
    t, c = retrieve_for_prompt("x", truth_base_path=None)
    assert isinstance(t, list)
    assert isinstance(c, list)
    assert len(t) == 0


def test_tokenizer_encode_decode_roundtrip():
    from tokenizer import BPETokenizer
    tok = BPETokenizer()
    tok.train(["hello world", "hello again"], vocab_size=256)
    enc = tok.encode("hello")
    dec = tok.decode(enc)
    assert "hello" in dec or dec == "hello"
    enc2 = tok.encode(dec)
    assert enc == enc2 or tok.decode(enc2) == dec


def test_tokenizer_unicode_roundtrip():
    """Encode/decode string with spaces, punctuation, non-ASCII; decode is non-empty and does not crash."""
    from tokenizer import BPETokenizer
    tok = BPETokenizer()
    tok.train(["hello world — test", "hello world", "—"], vocab_size=256)
    s = "hello world — test"
    enc = tok.encode(s)
    dec = tok.decode(enc)
    assert isinstance(dec, str)
    assert len(dec) > 0


def test_gpt_forward_shape():
    from model.gpt import GPT
    model = GPT(vocab_size=100, context_len=32, d_model=64, n_layers=2, n_heads=4, d_ff=256)
    x = torch.randint(0, 100, (2, 32))
    logits = model(x)
    assert logits.shape == (2, 32, 100)
    logits2, loss = model(x, targets=x)
    assert logits2.shape == (2, 32, 100)
    assert loss.dim() == 0
    assert loss.item() >= 0


def test_gpt_forward_batch1_context1():
    """Forward with batch_size=1, context_len=1 yields shape (1, 1, vocab_size)."""
    from model.gpt import GPT
    model = GPT(vocab_size=50, context_len=1, d_model=64, n_layers=2, n_heads=4, d_ff=256)
    x = torch.randint(0, 50, (1, 1))
    logits = model(x)
    assert logits.shape == (1, 1, 50)
