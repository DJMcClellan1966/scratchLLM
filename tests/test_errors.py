"""Tests for errors: imports, basic instantiation, and explicit error paths (exceptions or graceful handling)."""
from pathlib import Path

import pytest


def test_import_config():
    from config.scaling import ModelScale, compute_scale
    assert ModelScale is not None
    assert compute_scale is not None


def test_import_data():
    from data.schema import Document
    from data.corpus import build_corpus, load_manifest, load_corpus_jsonl
    assert Document is not None
    assert build_corpus is not None


def test_import_base():
    from base.tiers import Tier, tier_from_source
    from base.truth_base import Statement, load_truth_base, save_truth_base
    from base.structure import format_context, FormattedContext
    from base.retrieve import retrieve_for_prompt, retrieve_truth_base
    from base.language import parse_to_meaning, meaning_to_text, conflict, resolve_conflicts
    assert Tier is not None
    assert format_context is not None
    assert parse_to_meaning is not None


def test_import_tokenizer():
    from tokenizer import BPETokenizer, load_tokenizer, save_tokenizer
    assert BPETokenizer is not None


def test_import_model():
    from model.gpt import GPT
    from model.attention import CausalSelfAttention
    from model.block import GPTBlock
    assert GPT is not None


def test_import_train():
    from train.dataset import CorpusDataset
    from train.config import TrainConfig
    from train.train import train_model
    assert CorpusDataset is not None
    assert TrainConfig is not None


def test_import_inference():
    from inference.generate import load_model_and_tokenizer, generate, generate_with_base
    assert generate is not None
    assert generate_with_base is not None


def test_config_scale_instantiation():
    from config.scaling import compute_scale, ModelScale
    scale = compute_scale(1000, 100, 50)
    assert isinstance(scale, ModelScale)
    assert scale.vocab_size >= 512
    assert scale.context_len >= 64
    assert scale.d_model % scale.n_heads == 0


def test_config_scale_invalid_raises():
    from config.scaling import ModelScale
    with pytest.raises(ValueError):
        ModelScale(vocab_size=100, context_len=64, d_model=256, n_layers=2, n_heads=7, d_ff=1024)


def test_document_schema():
    from data.schema import Document
    d = Document(text="hello", source="test", meta={"k": 1})
    assert d.text == "hello"
    assert d.source == "test"
    d2 = Document.from_dict(d.to_dict())
    assert d2.text == d.text
    assert d2.meta == d.meta


def test_compute_scale_zero_tokens_does_not_raise():
    """compute_scale(0,0,0) forces n_tokens=1 and does not raise."""
    from config.scaling import compute_scale
    scale = compute_scale(0, 0, 0)
    assert scale.vocab_size >= 512
    assert scale.context_len >= 64


def test_model_scale_invalid_n_heads_raises():
    """ModelScale with d_model not divisible by n_heads raises ValueError."""
    from config.scaling import ModelScale
    with pytest.raises(ValueError):
        ModelScale(
            vocab_size=64, context_len=32, d_model=64,
            n_layers=2, n_heads=7, d_ff=256,
        )


def test_document_from_dict_empty():
    """Document.from_dict({}) returns doc with empty text and source 'unknown'."""
    from data.schema import Document
    d = Document.from_dict({})
    assert d.text == ""
    assert d.source == "unknown"
    assert d.meta == {}


def test_document_from_dict_non_string_text():
    """Document.from_dict({'text': 123}) does not coerce; current behavior accepts int (no crash)."""
    from data.schema import Document
    d = Document.from_dict({"text": 123})
    assert d.text == 123  # current implementation does not coerce to str
    assert d.source == "unknown"


def test_load_truth_base_nonexistent_returns_empty():
    """load_truth_base(nonexistent_path) returns []."""
    from base.truth_base import load_truth_base
    result = load_truth_base(Path("/nonexistent/truth_base.jsonl"))
    assert result == []


def test_load_manifest_nonexistent_raises():
    """load_manifest(nonexistent_path) raises FileNotFoundError."""
    from data.corpus import load_manifest
    with pytest.raises(FileNotFoundError):
        load_manifest(Path("/nonexistent/manifest.json"))


def test_load_corpus_jsonl_nonexistent_raises():
    """load_corpus_jsonl(nonexistent_path) raises FileNotFoundError."""
    from data.corpus import load_corpus_jsonl
    with pytest.raises(FileNotFoundError):
        load_corpus_jsonl(Path("/nonexistent/corpus.jsonl"))


def test_load_tokenizer_nonexistent_raises():
    """load_tokenizer(nonexistent_dir) raises FileNotFoundError."""
    from tokenizer import load_tokenizer
    with pytest.raises(FileNotFoundError):
        load_tokenizer(Path("/nonexistent/tokenizer_dir"))


def test_tokenizer_encode_empty_string():
    """With trained tokenizer, encode('') returns [] or defined list; decode does not crash."""
    from tokenizer import BPETokenizer
    tok = BPETokenizer()
    tok.train(["hello world"], vocab_size=256)
    enc = tok.encode("")
    assert isinstance(enc, list)
    decoded = tok.decode(enc)
    assert isinstance(decoded, str)


def test_generate_empty_prompt_returns_string():
    """generate(model, tokenizer, '') returns a string and does not crash."""
    from model.gpt import GPT
    from tokenizer import BPETokenizer
    from inference.generate import generate
    tok = BPETokenizer()
    tok.train(["a b c"], vocab_size=64)
    model = GPT(
        vocab_size=tok.vocab_size, context_len=16, d_model=64,
        n_layers=2, n_heads=4, d_ff=256,
    )
    out = generate(model, tok, "", max_new_tokens=2)
    assert isinstance(out, str)
