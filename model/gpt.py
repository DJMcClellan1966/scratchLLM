"""Decoder-only GPT: embedding, N blocks, final norm, LM head. CPU-first."""
import torch
import torch.nn as nn
from .block import GPTBlock


class GPT(nn.Module):
    """GPT-style decoder-only language model. Hyperparams from config.scaling.ModelScale."""

    def __init__(
        self,
        vocab_size: int,
        context_len: int,
        d_model: int,
        n_layers: int,
        n_heads: int,
        d_ff: int,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.context_len = context_len
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.token_embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(context_len, d_model)
        self.drop = nn.Dropout(dropout)
        self.blocks = nn.ModuleList(
            [
                GPTBlock(d_model, n_heads, context_len, d_ff, dropout)
                for _ in range(n_layers)
            ]
        )
        self.ln_f = nn.LayerNorm(d_model)
        self.lm_head = nn.Linear(d_model, vocab_size, bias=False)
        # Tie weights optional: self.lm_head.weight = self.token_embed.weight
        self.apply(self._init_weights)

    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, idx: torch.Tensor, targets: torch.Tensor | None = None) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
        # idx: (B, T)
        B, T = idx.shape
        pos = torch.arange(0, T, dtype=torch.long, device=idx.device)
        x = self.token_embed(idx) + self.pos_embed(pos)
        x = self.drop(x)
        for block in self.blocks:
            x = block(x)
        x = self.ln_f(x)
        logits = self.lm_head(x)
        if targets is None:
            return logits
        loss = torch.nn.functional.cross_entropy(
            logits.view(-1, self.vocab_size),
            targets.view(-1),
            ignore_index=-1,
        )
        return logits, loss

    @property
    def device(self) -> torch.device:
        return next(self.parameters()).device
