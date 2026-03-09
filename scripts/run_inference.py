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

from inference.generate import load_model_and_tokenizer, generate, generate_with_base


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
    ap.add_argument("--truth-base", type=Path, default=None, help="Path to truth_base.jsonl for meaning base")
    ap.add_argument("--corpus", type=Path, default=None, help="Path to corpus.jsonl for retrieval")
    ap.add_argument("--ir", type=Path, default=None, help="Path to IR JSONL for formal-only fallback or retrieval")
    ap.add_argument("--use-base", action="store_true", help="Use truth base + corpus retrieval for context")
    ap.add_argument("--use-meaning", action="store_true", help="Use meaning-language retrieval and conflict resolution")
    ap.add_argument("--max-tier", type=int, default=2, help="Max tier (0-2) for truth retrieval; lower = stricter")
    ap.add_argument("--show-ids", action="store_true", help="Print Gödel IDs of truth statements used")
    ap.add_argument("--show-tiers", action="store_true", help="Print tier summary for cited statements")
    ap.add_argument("--fallback-formal", action="store_true", help="If checkpoint/tokenizer missing, use formal-only response (requires --truth-base or --ir)")
    ap.add_argument("--check-consistency", action="store_true", help="Warn if truth base/IR inconsistent before running")
    ap.add_argument("--vertical", type=str, default=None, help="Vertical preset (e.g. general, medical, legal); uses default paths and max_tier from config")
    args = ap.parse_args()

    truth_base_path = args.truth_base
    ir_path = args.ir
    max_tier = args.max_tier
    if args.vertical:
        from base.vertical import resolve_vertical
        truth_base_path, ir_path, max_tier, found = resolve_vertical(
            args.vertical, args.truth_base, args.ir, args.max_tier, ROOT
        )
        if not found:
            print(f"Unknown vertical: {args.vertical}. Using explicit paths only.", file=sys.stderr)

    # Fallback: no checkpoint/tokenizer but --fallback-formal and (truth-base or ir) -> formal-only
    if args.fallback_formal and (not args.checkpoint.exists() or not args.tokenizer.exists()):
        if not truth_base_path and not ir_path:
            print("Provide --truth-base or --ir for fallback (or use --vertical with a preset that has defaults).", file=sys.stderr)
            sys.exit(1)
        from base import respond_formal_only
        query = args.prompt or "What is truth?"
        result = respond_formal_only(
            query,
            truth_base_path=truth_base_path,
            ir_path=ir_path,
            top_k=5,
            max_tier=max_tier,
            resolve=True,
        )
        _safe_print(result[0] or "(no matching statements)")
        if args.show_ids and result[1]:
            _safe_print("")
            _safe_print("Gödel IDs: " + ", ".join(str(n) for n in result[1]))
        sys.exit(0)

    if not args.checkpoint.exists():
        print("Checkpoint not found:", args.checkpoint)
        sys.exit(1)
    if not args.tokenizer.exists():
        print("Tokenizer dir not found:", args.tokenizer)
        sys.exit(1)

    use_base = args.use_base and (truth_base_path or args.corpus)
    if use_base and args.check_consistency and (truth_base_path or ir_path):
        from base import check_consistency_of_paths
        consistent, pairs = check_consistency_of_paths(
            truth_base_path=truth_base_path,
            ir_path=ir_path,
        )
        if not consistent:
            print(f"Warning: truth base/IR inconsistent ({len(pairs)} conflicting pair(s)). Proceeding anyway.", file=sys.stderr)

    print("Loading model and tokenizer...")
    model, tokenizer = load_model_and_tokenizer(
        args.checkpoint,
        args.tokenizer,
        device=args.device,
    )
    corpus_path = args.corpus
    if corpus_path and corpus_path.is_dir():
        corpus_path = corpus_path / "corpus.jsonl"
    show_citations = args.show_ids or args.show_tiers
    if use_base:
        def gen_fn(p: str):
            result = generate_with_base(
                model, tokenizer, p,
                truth_base_path=truth_base_path,
                corpus_path=corpus_path,
                use_base=True,
                use_meaning=args.use_meaning,
                max_new_tokens=args.max_tokens,
                temperature=args.temperature,
                top_k=args.top_k,
                max_tier_truth=max_tier,
                return_citations=show_citations and args.use_meaning,
            )
            return result
    else:
        def gen_fn(p: str):
            return generate(model, tokenizer, p, max_new_tokens=args.max_tokens, temperature=args.temperature, top_k=args.top_k)

    def print_result(out):
        if isinstance(out, tuple) and len(out) >= 2:
            text, ids, tiers = out[0], out[1], (out[2] if len(out) > 2 else [])
            _safe_print(text)
            if args.show_tiers and tiers:
                _safe_print("")
                _safe_print("Tiers: " + ", ".join(str(t) for t in tiers if t is not None))
            if args.show_ids and ids:
                _safe_print("")
                _safe_print("Gödel IDs: " + ", ".join(str(n) for n in ids))
        else:
            _safe_print(out)

    if args.prompt:
        out = gen_fn(args.prompt)
        print_result(out)
    else:
        print("Interactive mode (empty line to exit).")
        while True:
            try:
                prompt = input("> ").strip()
                if not prompt:
                    break
                out = gen_fn(prompt)
                print_result(out)
                print()
            except (EOFError, KeyboardInterrupt):
                break


if __name__ == "__main__":
    main()
