"""Scale model hyperparameters from corpus size (actual + inferred tokens)."""
from dataclasses import dataclass
import math


@dataclass
class ModelScale:
    """Model hyperparameters derived from corpus size."""

    vocab_size: int
    context_len: int
    d_model: int
    n_layers: int
    n_heads: int
    d_ff: int  # FFN hidden dim, typically 4 * d_model

    def __post_init__(self) -> None:
        if self.d_model % self.n_heads != 0:
            raise ValueError("d_model must be divisible by n_heads")


def compute_scale(
    n_tokens_actual: int,
    n_tokens_inferred: int = 0,
    n_docs: int = 0,
) -> ModelScale:
    """
    Compute model scale from corpus stats.
    Small corpora get small models (CPU-friendly); larger corpora get larger models.
    """
    n_tokens = n_tokens_actual + n_tokens_inferred
    if n_tokens < 1:
        n_tokens = 1

    # Vocab: cap at 8k; grow with sqrt(tokens) for small corpora
    vocab_size = min(8192, max(512, 500 + int(math.sqrt(n_tokens))))

    # Context length: small for tiny corpora to avoid overfitting long sequences
    context_len = min(512, max(64, 64 + n_tokens // 10000))

    # d_model: 256–512 for <1M tokens, 512–768 for 1M–10M
    if n_tokens < 500_000:
        d_model = 256
    elif n_tokens < 1_000_000:
        d_model = 384
    elif n_tokens < 5_000_000:
        d_model = 512
    elif n_tokens < 10_000_000:
        d_model = 768
    else:
        d_model = 768

    # Ensure multiple of 64 for efficiency
    d_model = (d_model // 64) * 64
    if d_model < 64:
        d_model = 64

    # Layers: 2–4 for small, 4–6 for medium, 6–8 for larger
    if n_tokens < 500_000:
        n_layers = 2
    elif n_tokens < 2_000_000:
        n_layers = 4
    elif n_tokens < 5_000_000:
        n_layers = 6
    else:
        n_layers = 8

    n_heads = 4 if d_model < 384 else 8
    if d_model % n_heads != 0:
        n_heads = 4

    d_ff = 4 * d_model

    return ModelScale(
        vocab_size=vocab_size,
        context_len=context_len,
        d_model=d_model,
        n_layers=n_layers,
        n_heads=n_heads,
        d_ff=d_ff,
    )
