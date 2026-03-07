"""Load checkpoint + tokenizer; autoregressive generation with temperature/top-k. CPU."""
from pathlib import Path
from typing import Optional

import torch

from config.scaling import ModelScale
from model.gpt import GPT
from tokenizer import BPETokenizer, load_tokenizer


def load_model_and_tokenizer(
    checkpoint_path: str | Path,
    tokenizer_path: str | Path,
    scale: Optional[ModelScale] = None,
    device: str = "cpu",
) -> tuple[GPT, BPETokenizer]:
    """Load model from checkpoint and tokenizer from dir. Scale from checkpoint or passed in."""
    checkpoint_path = Path(checkpoint_path)
    tokenizer_path = Path(tokenizer_path)
    tokenizer = load_tokenizer(tokenizer_path)
    if scale is None:
        scale = _scale_from_checkpoint_dir(checkpoint_path) or _default_scale(tokenizer.vocab_size)
    device = torch.device(device)
    model = GPT(
        vocab_size=scale.vocab_size,
        context_len=scale.context_len,
        d_model=scale.d_model,
        n_layers=scale.n_layers,
        n_heads=scale.n_heads,
        d_ff=scale.d_ff,
    ).to(device)
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=True)
    if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
        model.load_state_dict(ckpt["model_state_dict"], strict=True)
    else:
        model.load_state_dict(ckpt, strict=True)
    model.eval()
    return model, tokenizer


def _scale_from_checkpoint_dir(checkpoint_path: Path) -> Optional[ModelScale]:
    """Try to load scale from manifest or scale.json next to checkpoint."""
    dir_path = checkpoint_path.parent
    scale_file = dir_path / "scale.json"
    if not scale_file.exists():
        return None
    import json
    with open(scale_file, encoding="utf-8") as f:
        d = json.load(f)
    return ModelScale(
        vocab_size=d["vocab_size"],
        context_len=d["context_len"],
        d_model=d["d_model"],
        n_layers=d["n_layers"],
        n_heads=d["n_heads"],
        d_ff=d["d_ff"],
    )


def _default_scale(vocab_size: int) -> ModelScale:
    return ModelScale(
        vocab_size=vocab_size,
        context_len=256,
        d_model=256,
        n_layers=4,
        n_heads=4,
        d_ff=1024,
    )


def generate(
    model: GPT,
    tokenizer: BPETokenizer,
    prompt: str,
    max_new_tokens: int = 100,
    temperature: float = 0.8,
    top_k: Optional[int] = 40,
) -> str:
    """Autoregressive generation. Returns prompt + generated text."""
    model.eval()
    device = model.device
    ids = tokenizer.encode(prompt)
    if not ids:
        ids = [0]
    context_len = model.context_len
    if len(ids) > context_len:
        ids = ids[-context_len:]
    with torch.no_grad():
        for _ in range(max_new_tokens):
            x = torch.tensor([ids[-context_len:]], dtype=torch.long, device=device)
            logits = model(x)
            logits = logits[0, -1, :] / max(temperature, 1e-5)
            if top_k is not None:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[-1]] = float("-inf")
            probs = torch.softmax(logits, dim=-1)
            next_id = torch.multinomial(probs, num_samples=1).item()
            ids.append(next_id)
            eos_id = tokenizer.vocab.get("<|eos|>")
            if eos_id is not None and next_id == eos_id:
                break
    return tokenizer.decode(ids)
