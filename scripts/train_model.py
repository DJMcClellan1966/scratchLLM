#!/usr/bin/env python3
"""Train tokenizer (if needed) and model on built corpus. Reads corpus dir and manifest."""
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.scaling import compute_scale, ModelScale
from data.corpus import build_corpus, load_manifest, load_corpus_jsonl
from tokenizer import BPETokenizer, save_tokenizer, load_tokenizer
from train.config import TrainConfig
from train.train import train_model


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Train scratchLLM on corpus")
    ap.add_argument("corpus_dir", type=Path, nargs="?", default=Path("corpus"), help="Corpus directory (with corpus.jsonl, manifest.json)")
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--use-tier-tags", action="store_true", help="Prepend [USER] to corpus chunks")
    ap.add_argument("--use-truth-base-mixing", action="store_true", help="Randomly prefix some chunks with [FACT] truth base")
    ap.add_argument("--truth-base", type=Path, default=None, help="Path to truth_base.jsonl for mixing")
    args = ap.parse_args()

    corpus_dir = Path(args.corpus_dir)
    manifest_path = corpus_dir / "manifest.json"
    if not manifest_path.exists():
        print("No manifest.json in", corpus_dir, "- run build_corpus first.")
        sys.exit(1)
    manifest = load_manifest(manifest_path)
    scale = compute_scale(
        manifest.n_tokens_actual,
        manifest.n_tokens_inferred,
        manifest.n_docs,
    )
    tokenizer_dir = corpus_dir / "tokenizer"
    if not (tokenizer_dir / "vocab.json").exists():
        print("Training tokenizer...")
        docs = load_corpus_jsonl(corpus_dir / "corpus.jsonl")
        texts = [d.text for d in docs]
        tokenizer = BPETokenizer()
        tokenizer.train(texts, vocab_size=scale.vocab_size)
        save_tokenizer(tokenizer, tokenizer_dir)
        print("Tokenizer saved to", tokenizer_dir)
    train_config = TrainConfig(
        batch_size=args.batch_size or 8,
        context_len=scale.context_len,
        max_epochs=args.epochs or 3,
        output_dir=corpus_dir / "checkpoints",
        device=args.device,
        use_tier_tags=args.use_tier_tags,
        use_truth_base_mixing=args.use_truth_base_mixing,
        truth_base_path=args.truth_base if args.truth_base is not None else (ROOT / "base" / "truth_base.jsonl") if args.use_truth_base_mixing else None,
    )
    if args.batch_size is not None:
        train_config.batch_size = args.batch_size
    if args.epochs is not None:
        train_config.max_epochs = args.epochs
    print("Training model...")
    out_dir = train_model(
        corpus_dir=corpus_dir,
        manifest_path=manifest_path,
        tokenizer_path=tokenizer_dir,
        scale=scale,
        train_config=train_config,
    )
    print("Checkpoints and scale.json saved to", out_dir)


if __name__ == "__main__":
    main()
