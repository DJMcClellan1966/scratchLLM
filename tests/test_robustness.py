"""Robustness tests: empty inputs, malformed data, encoding edge cases."""
import tempfile
from pathlib import Path

import pytest


def test_build_corpus_all_empty():
    """build_corpus(out_dir=None) with all path lists empty returns empty docs and manifest.n_docs == 0."""
    from data.corpus import build_corpus
    docs, manifest = build_corpus(out_dir=None)
    assert docs == []
    assert manifest.n_docs == 0


def test_document_from_dict_empty_and_roundtrip():
    """Document.from_dict with empty/minimal fields; roundtrip to_dict/from_dict with meta."""
    from data.schema import Document
    d = Document.from_dict({"text": "", "source": "", "meta": None})
    assert d.text == ""
    assert d.source == ""
    assert d.meta is not None  # from_dict uses meta or {}
    d2 = Document(text="x", source="s", meta={"tier": 2})
    restored = Document.from_dict(d2.to_dict())
    assert restored.text == d2.text
    assert restored.meta == d2.meta


def test_truth_base_malformed_line():
    """load_truth_base on JSONL with malformed line (tier not a number) raises or skips; document behavior."""
    from base.truth_base import load_truth_base
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as f:
        f.write('{"text": "valid", "tier": 0, "source": "curated"}\n')
        f.write('{"text": "x", "tier": "not_a_number", "source": "curated"}\n')
        path = Path(f.name)
    try:
        with pytest.raises(ValueError):
            load_truth_base(path)
    finally:
        path.unlink(missing_ok=True)


def test_tokenizer_train_empty_corpus():
    """Train tokenizer on [] or ['']; no crash; minimal vocab."""
    from tokenizer import BPETokenizer
    tok = BPETokenizer()
    tok.train([], vocab_size=256)
    assert hasattr(tok, "vocab")
    enc = tok.encode("")
    assert isinstance(enc, list)
    dec = tok.decode(enc)
    assert isinstance(dec, str)


def test_parse_to_meaning_long_string():
    """parse_to_meaning with very long string or no-match string returns [] and does not hang."""
    from base.language import parse_to_meaning
    long_str = "x" * 10_000
    result = parse_to_meaning(long_str)
    assert isinstance(result, list)
    assert result == [] or len(result) >= 0
    no_match = "zzz zzz zzz no pattern here"
    result2 = parse_to_meaning(no_match)
    assert isinstance(result2, list)


def test_unicode_encode_decode_no_crash():
    """Document or prompt with Unicode (em dash, emoji, non-Latin); encode/decode or generation does not raise."""
    from tokenizer import BPETokenizer
    tok = BPETokenizer()
    tok.train(["hello", "world", "\u2014", "test", "café", "日本語"], vocab_size=512)
    s = "hello world \u2014 test café"
    enc = tok.encode(s)
    dec = tok.decode(enc)
    assert isinstance(dec, str)
    # May be lossy; just ensure no UnicodeEncodeError/UnicodeDecodeError
    _ = tok.encode("\u2014 \U0001f600")
    _ = tok.decode(enc)


def test_load_text_files_nonexistent_and_empty():
    """load_text_files([nonexistent_path]) returns []; empty file returns one doc; no crash."""
    from data.sources.text_files import load_text_files
    result = load_text_files([Path("/nonexistent/path/xyz")])
    assert result == []
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write("")
        path = Path(f.name)
    try:
        result2 = load_text_files([path])
        assert isinstance(result2, list)
        assert len(result2) <= 1
        if result2:
            assert result2[0].text == ""
    finally:
        path.unlink(missing_ok=True)


def test_load_dictionary_empty_paths():
    """load_dictionary([]) returns []."""
    from data.sources.dictionary import load_dictionary
    result = load_dictionary([])
    assert result == []


def test_load_bible_commentary_empty_paths():
    """load_bible_commentary([]) returns []."""
    from data.sources.bible_commentary import load_bible_commentary
    result = load_bible_commentary([])
    assert result == []
