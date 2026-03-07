"""Pre-norm decoder block: attention + residual, FFN + residual (Raschka-style)."""
import torch
import torch.nn as nn
from .attention import CausalSelfAttention


class GPTBlock(nn.Module):
    """Single decoder block: LayerNorm -> CausalSelfAttention -> residual, LayerNorm -> FFN -> residual."""

    def __init__(self, d_model: int, n_heads: int, context_len: int, d_ff: int, dropout: float = 0.1):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = CausalSelfAttention(d_model, n_heads, context_len, dropout)
        self.ln2 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln1(x))
        x = x + self.ffn(self.ln2(x))
        return x
