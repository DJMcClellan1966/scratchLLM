"""Causal self-attention (Raschka-style). Position i sees only positions <= i."""
import math
import torch
import torch.nn as nn


class CausalSelfAttention(nn.Module):
    """Multi-head causal self-attention. Mask ensures no lookahead."""

    def __init__(self, d_model: int, n_heads: int, context_len: int, dropout: float = 0.1):
        super().__init__()
        assert d_model % n_heads == 0
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.context_len = context_len
        self.qkv = nn.Linear(d_model, 3 * d_model)
        self.out = nn.Linear(d_model, d_model)
        self.dropout = nn.Dropout(dropout)
        # Causal mask: (1, 1, context_len, context_len)
        mask = torch.tril(torch.ones(context_len, context_len)).view(1, 1, context_len, context_len)
        self.register_buffer("causal_mask", mask)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, d_model)
        B, T, C = x.shape
        qkv = self.qkv(x)
        q, k, v = qkv.split(self.d_model, dim=-1)
        # Reshape for multi-head: (B, T, n_heads, head_dim) -> (B, n_heads, T, head_dim)
        q = q.view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        k = k.view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        v = v.view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        # Attention scores
        scale = 1.0 / math.sqrt(self.head_dim)
        att = (q @ k.transpose(-2, -1)) * scale
        # Causal mask: -inf where mask == 0
        mask = self.causal_mask[:, :, :T, :T]
        att = att.masked_fill(mask == 0, float("-inf"))
        att = torch.softmax(att, dim=-1)
        att = self.dropout(att)
        out = (att @ v).transpose(1, 2).contiguous().view(B, T, C)
        return self.out(out)
