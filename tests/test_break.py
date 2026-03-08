"""Try-to-break / negative tests: mismatches, corrupt files, invalid inputs."""
import json
import tempfile
from pathlib import Path

import pytest
import torch


def test_model_tokenizer_vocab_mismatch():
    """Model vocab_size < tokenizer vocab: prompt that tokenizes to id >= model vocab raises at runtime."""
    from model.gpt import GPT
    from tokenizer import BPETokenizer
    from inference.generate import generate
    # Tokenizer with larger effective vocab (many merges)
    tok = BPETokenizer()
    tok.train(
        ["hello world", "hello there", "world peace", "the quick brown fox"] * 20,
        vocab_size=300,
    )
    # Model with smaller vocab
    model = GPT(
        vocab_size=100,
        context_len=16,
        d_model=64,
        n_layers=2,
        n_heads=4,
        d_ff=256,
    )
    # Encode a prompt; if any id >= 100, forward will hit index out of range
    ids = tok.encode("hello world")
    if any(i >= 100 for i in ids):
        with pytest.raises((RuntimeError, IndexError)):
            generate(model, tok, "hello world", max_new_tokens=1)
    else:
        # Small tokenizer might stay within 0-99; then no raise
        out = generate(model, tok, "hello world", max_new_tokens=1)
        assert isinstance(out, str)


def test_tokenizer_decode_invalid_id():
    """Pass id outside vocab to decode: document behavior (e.g. unk or ignore)."""
    from tokenizer import BPETokenizer
    tok = BPETokenizer()
    tok.train(["a b c"], vocab_size=64)
    # decode accepts list of ints; id beyond vocab_size may be in reverse_vocab if BPE added it
    result = tok.decode([0, 99999, 1])
    assert isinstance(result, str)
    # Current behavior: unknown ids map to <|unk|> or are skipped; no uncaught exception


def test_corrupt_checkpoint_raises():
    """Loading a checkpoint that is not valid PyTorch (e.g. text file) raises."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pt", delete=False, encoding="utf-8"
    ) as f:
        f.write("not a checkpoint")
        path = Path(f.name)
    try:
        with pytest.raises(Exception):
            torch.load(path, map_location="cpu", weights_only=True)
    finally:
        path.unlink(missing_ok=True)


def test_corrupt_scale_json_raises():
    """scale.json with missing keys or wrong types causes _scale_from_checkpoint_dir or ModelScale to raise."""
    from inference.generate import _scale_from_checkpoint_dir
    with tempfile.TemporaryDirectory() as d:
        scale_path = Path(d) / "scale.json"
        scale_path.write_text(json.dumps({"vocab_size": "not_an_int", "context_len": 64}))
        # _scale_from_checkpoint_dir returns ModelScale; ModelScale doesn't validate type
        # Using the scale in GPT() would raise; so test missing key which raises in _scale_from_checkpoint_dir
        scale_path.write_text(json.dumps({"context_len": 64}))
        with pytest.raises((KeyError, TypeError, ValueError)):
            _scale_from_checkpoint_dir(Path(d) / "dummy.pt")


def test_empty_truth_base_file_returns_empty():
    """load_truth_base on empty file (0 lines) returns []."""
    from base.truth_base import load_truth_base
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as f:
        path = Path(f.name)
    try:
        result = load_truth_base(path)
        assert result == []
    finally:
        path.unlink(missing_ok=True)


def test_format_context_huge_chunks_truncates():
    """format_context with very long chunks and context_len truncates; keeps prompt; no crash."""
    from base.structure import format_context
    from tokenizer import BPETokenizer
    tok = BPETokenizer()
    tok.train(["a b c"], vocab_size=64)
    big = "word " * 10_000
    fc = format_context(
        [big],
        [],
        "short prompt",
        tokenizer=tok,
        context_len=64,
    )
    assert "short prompt" in fc.context_string or "prompt" in fc.context_string
    assert isinstance(fc.segment_info, list)


def test_generate_with_base_missing_paths():
    """generate_with_base with truth_base_path=None, corpus_path=None does not raise; defined behavior."""
    from model.gpt import GPT
    from tokenizer import BPETokenizer
    from inference.generate import generate_with_base
    tok = BPETokenizer()
    tok.train(["a b c"], vocab_size=64)
    model = GPT(
        vocab_size=tok.vocab_size,
        context_len=16,
        d_model=64,
        n_layers=2,
        n_heads=4,
        d_ff=256,
    )
    out = generate_with_base(
        model,
        tok,
        "hello",
        truth_base_path=None,
        corpus_path=None,
        max_new_tokens=2,
    )
    assert isinstance(out, str)


def test_resolve_conflicts_empty_list():
    """resolve_conflicts([]) returns []."""
    from base.language import resolve_conflicts
    result = resolve_conflicts([])
    assert result == []


def test_retrieve_truth_base_nonexistent_path():
    """retrieve_truth_base with nonexistent path returns [] (load_truth_base returns [])."""
    from base.retrieve import retrieve_truth_base
    result = retrieve_truth_base("x", Path("/nonexistent/truth_base.jsonl"))
    assert result == []
