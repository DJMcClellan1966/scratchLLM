"""Basic performance / smoke tests: timings and sanity checks."""
import time
from pathlib import Path

import pytest
import torch

# Project root
ROOT = Path(__file__).resolve().parent.parent


def test_scale_compute_performance():
    """compute_scale should complete in negligible time."""
    from config.scaling import compute_scale
    t0 = time.perf_counter()
    for _ in range(1000):
        compute_scale(100_000, 10_000, 500)
    elapsed = time.perf_counter() - t0
    assert elapsed < 2.0, "compute_scale 1000x should be under 2s"


def test_tokenizer_encode_performance():
    """Encode ~10k chars should complete in reasonable time."""
    from tokenizer import BPETokenizer
    tok = BPETokenizer()
    tok.train(["word " * 500], vocab_size=512)
    text = "hello world. " * 500
    t0 = time.perf_counter()
    for _ in range(10):
        tok.encode(text)
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0, "10x encode of ~6k chars should be under 5s"


def test_model_forward_performance():
    """One forward pass (small model) should complete in reasonable time on CPU."""
    from model.gpt import GPT
    model = GPT(vocab_size=256, context_len=64, d_model=128, n_layers=2, n_heads=4, d_ff=512)
    x = torch.randint(0, 256, (4, 64))
    t0 = time.perf_counter()
    for _ in range(5):
        model(x)
    elapsed = time.perf_counter() - t0
    assert elapsed < 15.0, "5 forward passes (batch 4, len 64) should be under 15s on CPU"


def test_build_corpus_smoke():
    """Build corpus on empty/minimal input should not crash."""
    from data.corpus import build_corpus
    docs, manifest = build_corpus(out_dir=None)
    assert manifest.n_docs >= 0
    assert len(docs) == manifest.n_docs


def test_format_context_truncate():
    """format_context with tokenizer and context_len should truncate."""
    from base.structure import format_context
    from tokenizer import BPETokenizer
    tok = BPETokenizer()
    tok.train(["a b c"], vocab_size=128)
    long_fact = "word " * 200
    fc = format_context([long_fact], [], "q", tokenizer=tok, context_len=64)
    ids = tok.encode(fc.context_string)
    assert len(ids) <= 64
