"""Training config: batch size, epochs, lr; can derive from scaling/corpus size."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TrainConfig:
    batch_size: int = 8
    context_len: int = 256
    max_epochs: int = 3
    learning_rate: float = 3e-4
    warmup_steps: int = 100
    checkpoint_every_steps: int = 500
    output_dir: str | Path = "checkpoints"
    device: str = "cpu"
    seed: Optional[int] = 42
    use_tier_tags: bool = False
    use_truth_base_mixing: bool = False
    truth_base_path: Optional[str | Path] = None

    @classmethod
    def from_scale(cls, n_tokens: int, context_len: int, **overrides) -> "TrainConfig":
        """Derive training config from corpus size and context length."""
        batch_size = 8
        if n_tokens > 500_000:
            batch_size = 16
        if n_tokens > 2_000_000:
            batch_size = 32
        max_epochs = 3
        if n_tokens < 100_000:
            max_epochs = 5
        d = {
            "batch_size": batch_size,
            "context_len": context_len,
            "max_epochs": max_epochs,
            "learning_rate": 3e-4,
            "warmup_steps": min(100, n_tokens // (batch_size * context_len * 10)),
        }
        d.update(overrides)
        return cls(**d)
