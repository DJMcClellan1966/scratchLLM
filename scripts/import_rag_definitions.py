#!/usr/bin/env python3
"""
Import desktop dictionary rag_definitions.json into scratchLLM IR JSONL.

Source: single-line JSON object with keys = keywords, value = {definition, all_defs, word_id}.
Output: one JSONL line per entry (subject, definition) for use with --ir in run_fast_response,
GUI, or check_consistency. File is ~227MB; ensure sufficient RAM for json.load.
"""
import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Convert rag_definitions.json to scratchLLM IR JSONL (subject, definition per line)."
    )
    ap.add_argument("--input", type=Path, required=True, help="Path to rag_definitions.json")
    ap.add_argument("--output", type=Path, required=True, help="Output .jsonl path")
    ap.add_argument("--limit", type=int, default=None, help="Max number of entries to emit (default: all)")
    args = ap.parse_args()

    if not args.input.exists():
        print("Input file not found:", args.input, file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    print("Loading JSON (may use significant RAM for large files)...", file=sys.stderr)
    with open(args.input, encoding="utf-8") as f:
        obj = json.load(f)

    if not isinstance(obj, dict):
        print("Expected a JSON object (key = keyword).", file=sys.stderr)
        sys.exit(1)

    n = 0
    skipped = 0
    with open(args.output, "w", encoding="utf-8") as out:
        for keyword, data in obj.items():
            if args.limit is not None and n >= args.limit:
                break
            if not isinstance(data, dict):
                skipped += 1
                continue
            definition = data.get("definition")
            if not definition and isinstance(data.get("all_defs"), list) and data["all_defs"]:
                definition = data["all_defs"][0]
            if not definition or not str(definition).strip():
                skipped += 1
                continue
            line = json.dumps(
                {"subject": keyword, "definition": str(definition).strip()},
                ensure_ascii=False,
            )
            out.write(line + "\n")
            n += 1
            if n % 50000 == 0 and n > 0:
                print(f"  wrote {n} entries...", file=sys.stderr)

    print(f"Wrote {n} entries to {args.output}", file=sys.stderr)
    if skipped:
        print(f"Skipped {skipped} entries (no definition).", file=sys.stderr)


if __name__ == "__main__":
    main()
