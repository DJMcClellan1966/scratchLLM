"""Load checkpoint + tokenizer; autoregressive generation with temperature/top-k. CPU."""
from pathlib import Path
from typing import Optional

import torch

from config.scaling import ModelScale
from model.gpt import GPT
from tokenizer import BPETokenizer, load_tokenizer

try:
    from base.retrieve import retrieve_for_prompt
    from base.structure import format_context
    _HAS_BASE = True
except ImportError:
    _HAS_BASE = False


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


def generate_with_base(
    model: GPT,
    tokenizer: BPETokenizer,
    prompt: str,
    truth_base_path: Optional[str | Path] = None,
    corpus_path: Optional[str | Path] = None,
    use_base: bool = True,
    use_meaning: bool = False,
    max_new_tokens: int = 100,
    temperature: float = 0.8,
    top_k: Optional[int] = 40,
    truth_top_k: int = 5,
    corpus_top_k: int = 5,
    max_tier_truth: int = 2,
    return_citations: bool = False,
) -> str | tuple[str, list[int], list]:
    """
    Generate with optional meaning base: retrieve from truth base + corpus, format with
    [FACT]/[CONTEXT]/[PROMPT], then run autoregressive generation. If use_meaning is True,
    retrieval uses the meaning language and conflicts are resolved by tier.
    If return_citations is True, returns (generated_text, list of Gödel IDs of truth statements used);
    otherwise returns generated_text only (backward compatible).
    """
    if not _HAS_BASE or not use_base or (not truth_base_path and not corpus_path):
        text = generate(model, tokenizer, prompt, max_new_tokens, temperature, top_k)
        return (text, []) if return_citations else text
    out = retrieve_for_prompt(
        prompt,
        truth_base_path=truth_base_path,
        corpus_path=corpus_path,
        truth_top_k=truth_top_k,
        corpus_top_k=corpus_top_k,
        max_tier_truth=max_tier_truth,
        use_meaning=use_meaning,
        resolve=use_meaning,
        return_truth_statements=return_citations and use_meaning,
    )
    if return_citations and use_meaning and len(out) == 3:
        truth_chunks, corpus_chunks, truth_statements = out
        citation_ids = []
        try:
            from base.godel import encode_statement
            for s in truth_statements:
                try:
                    citation_ids.append(encode_statement(s))
                except (TypeError, ValueError):
                    pass
        except ImportError:
            pass
        citation_tiers = [getattr(s, "tier", None) for s in truth_statements]
    else:
        truth_chunks = out[0]
        corpus_chunks = out[1]
        citation_ids = []
        citation_tiers = []
    formatted = format_context(
        truth_chunks,
        corpus_chunks,
        prompt,
        tokenizer=tokenizer,
        context_len=model.context_len,
    )
    text = generate(
        model,
        tokenizer,
        formatted.context_string,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_k=top_k,
    )
    if return_citations:
        return (text, citation_ids, citation_tiers)
    return text
