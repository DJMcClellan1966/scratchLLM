#!/usr/bin/env python3
"""Build corpus from user data paths. Writes corpus.jsonl and manifest.json to out_dir."""
import argparse
import sys
from pathlib import Path

# Project root = parent of scripts/
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.scaling import compute_scale
from data.corpus import build_corpus


def main() -> None:
    ap = argparse.ArgumentParser(description="Build user corpus for scratchLLM")
    ap.add_argument("--out-dir", type=Path, default=Path("corpus"), help="Output directory")
    ap.add_argument("--text", type=Path, nargs="*", default=[], help="Text file or dirs (.txt, .md)")
    ap.add_argument("--email", type=Path, nargs="*", default=[], help="Email mbox or .eml files")
    ap.add_argument("--social", type=Path, nargs="*", default=[], help="Social export JSON files/dirs")
    ap.add_argument("--bookmarks", type=Path, nargs="*", default=[], help="Browser bookmark JSON files")
    ap.add_argument("--readings", type=Path, nargs="*", default=[], help="Reading list export files")
    ap.add_argument("--fetch-urls", action="store_true", help="Fetch content from bookmark URLs")
    ap.add_argument("--fetch-delay", type=float, default=1.0, help="Delay between URL fetches (seconds)")
    args = ap.parse_args()

    docs, manifest = build_corpus(
        text_paths=[str(p) for p in args.text],
        email_paths=[str(p) for p in args.email],
        social_paths=[str(p) for p in args.social],
        bookmark_paths=[str(p) for p in args.bookmarks],
        reading_paths=[str(p) for p in args.readings],
        fetch_bookmark_urls=args.fetch_urls,
        fetch_delay=args.fetch_delay,
        out_dir=args.out_dir,
    )
    scale = compute_scale(
        manifest.n_tokens_actual,
        manifest.n_tokens_inferred,
        manifest.n_docs,
    )
    print(f"Documents: {manifest.n_docs}")
    print(f"Chars: {manifest.n_chars}")
    print(f"Tokens (est): {manifest.n_tokens_actual + manifest.n_tokens_inferred}")
    print("Suggested scale:", scale)
    print(f"Output: {args.out_dir / 'corpus.jsonl'}, {args.out_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
