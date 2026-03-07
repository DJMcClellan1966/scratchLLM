#!/usr/bin/env python3
"""Load model and tokenizer; run generation (CLI or interactive)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _safe_print(s: str) -> None:
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(s, flush=True)
    except (UnicodeEncodeError, UnicodeError):
        sys.stdout.buffer.write(s.encode(enc, errors="replace") + b"\n")
        sys.stdout.buffer.flush()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inference.generate import load_model_and_tokenizer, generate


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Run scratchLLM inference")
    ap.add_argument("--checkpoint", type=Path, default=Path("corpus/checkpoints/ckpt_final.pt"), help="Model checkpoint")
    ap.add_argument("--tokenizer", type=Path, default=Path("corpus/tokenizer"), help="Tokenizer directory")
    ap.add_argument("--prompt", type=str, default="", help="Prompt (or interactive if omitted)")
    ap.add_argument("--max-tokens", type=int, default=100)
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--top-k", type=int, default=40)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    if not args.checkpoint.exists():
        print("Checkpoint not found:", args.checkpoint)
        sys.exit(1)
    if not args.tokenizer.exists():
        print("Tokenizer dir not found:", args.tokenizer)
        sys.exit(1)

    print("Loading model and tokenizer...")
    model, tokenizer = load_model_and_tokenizer(
        args.checkpoint,
        args.tokenizer,
        device=args.device,
    )
    if args.prompt:
        out = generate(model, tokenizer, args.prompt, max_new_tokens=args.max_tokens, temperature=args.temperature, top_k=args.top_k)
        _safe_print(out)
    else:
        print("Interactive mode (empty line to exit).")
        while True:
            try:
                prompt = input("> ").strip()
                if not prompt:
                    break
                out = generate(model, tokenizer, prompt, max_new_tokens=args.max_tokens, temperature=args.temperature, top_k=args.top_k)
                _safe_print(out)
                print()
            except (EOFError, KeyboardInterrupt):
                break


if __name__ == "__main__":
    main()
