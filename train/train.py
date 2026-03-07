"""Training loop: next-token cross-entropy, AdamW, checkpointing. CPU by default."""
import json
import random
from pathlib import Path
from typing import Optional

import torch
from torch.utils.data import DataLoader

from config.scaling import ModelScale
from data.corpus import load_manifest
from model.gpt import GPT
from tokenizer import load_tokenizer
from train.config import TrainConfig
from train.dataset import CorpusDataset


def train_model(
    corpus_dir: str | Path,
    manifest_path: Optional[str | Path] = None,
    tokenizer_path: Optional[str | Path] = None,
    scale: Optional[ModelScale] = None,
    train_config: Optional[TrainConfig] = None,
    seed: Optional[int] = 42,
) -> Path:
    """
    Train GPT on corpus. Reads manifest for scaling, loads tokenizer, runs training loop.
    Returns path to output dir (checkpoints and tokenizer saved there).
    """
    corpus_dir = Path(corpus_dir)
    if manifest_path is None:
        manifest_path = corpus_dir / "manifest.json"
    manifest = load_manifest(manifest_path)
    if scale is None:
        from config.scaling import compute_scale
        scale = compute_scale(
            manifest.n_tokens_actual,
            manifest.n_tokens_inferred,
            manifest.n_docs,
        )
    if tokenizer_path is None:
        tokenizer_path = corpus_dir / "tokenizer"
    tokenizer = load_tokenizer(tokenizer_path)
    if train_config is None:
        train_config = TrainConfig.from_scale(
            manifest.n_tokens_actual + manifest.n_tokens_inferred,
            scale.context_len,
            output_dir=corpus_dir / "checkpoints",
            context_len=scale.context_len,
        )
    if seed is not None:
        random.seed(seed)
        torch.manual_seed(seed)
    device = torch.device(train_config.device)
    dataset = CorpusDataset(
        corpus_dir / "corpus.jsonl",
        tokenizer,
        train_config.context_len,
    )
    if len(dataset) == 0:
        raise ValueError("Dataset is empty; check corpus and tokenizer.")
    loader = DataLoader(
        dataset,
        batch_size=train_config.batch_size,
        shuffle=True,
        num_workers=0,
    )
    vocab_size = tokenizer.vocab_size
    model = GPT(
        vocab_size=vocab_size,
        context_len=scale.context_len,
        d_model=scale.d_model,
        n_layers=scale.n_layers,
        n_heads=scale.n_heads,
        d_ff=scale.d_ff,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=train_config.learning_rate)
    output_dir = Path(train_config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    scale_path = output_dir / "scale.json"
    with open(scale_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "vocab_size": vocab_size,
                "context_len": scale.context_len,
                "d_model": scale.d_model,
                "n_layers": scale.n_layers,
                "n_heads": scale.n_heads,
                "d_ff": scale.d_ff,
            },
            f,
            indent=2,
        )
    step = 0
    for epoch in range(train_config.max_epochs):
        model.train()
        for batch in loader:
            batch = batch.to(device)
            _, loss = model(batch, targets=batch)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            step += 1
            if step % 100 == 0:
                print(f"epoch {epoch + 1} step {step} loss {loss.item():.4f}")
            if step > 0 and step % train_config.checkpoint_every_steps == 0:
                ckpt_path = output_dir / f"ckpt_step_{step}.pt"
                torch.save({"step": step, "model_state_dict": model.state_dict()}, ckpt_path)
    final_path = output_dir / "ckpt_final.pt"
    torch.save({"step": step, "model_state_dict": model.state_dict()}, final_path)
    return output_dir
