#!/usr/bin/env python3
"""Run Gödel formal-system consistency on dictionary/ingestion IR (JSONL).

Usage:
  python scripts/run_godel_on_ir.py <path/to/pregenerated_ir.jsonl>
  python scripts/run_godel_on_ir.py "C:\...\dictionary\data\shannon\pregenerated_ir.jsonl"
  python scripts/run_godel_on_ir.py <path> --limit 500   # use first 500 lines (faster for large files)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from base import load_axioms_from_ir, is_consistent, conflicting_pairs, get_theorems
from base.godel import decode_statement


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Run Gödel consistency on IR JSONL")
    ap.add_argument("ir_path", type=Path, help="Path to pregenerated_ir.jsonl or ingestion_ir.jsonl")
    ap.add_argument("--no-meaning-derivations", action="store_true", help="Theorems = axioms only")
    ap.add_argument("--limit", type=int, default=None, help="Use only first N lines (for quick run on large files)")
    args = ap.parse_args()

    if not args.ir_path.exists():
        print("File not found:", args.ir_path, file=sys.stderr)
        sys.exit(1)

    line_count = sum(1 for _ in args.ir_path.open(encoding="utf-8") if _.strip())
    if args.limit is None and line_count > 2000:
        print(f"Note: file has {line_count} lines; Gödel decode can be slow. Use --limit N for a quicker run.", file=sys.stderr)

    if args.limit is not None:
        print(f"(Using first {args.limit} lines)")
    axioms = load_axioms_from_ir(args.ir_path, limit=args.limit)
    print(f"Axioms (Gödel numbers from IR): {len(axioms)}")

    theorems = get_theorems(axioms, include_meaning_derivations=not args.no_meaning_derivations)
    print(f"Theorems: {len(theorems)}")

    consistent = is_consistent(axioms)
    print(f"Consistent: {consistent}")

    if not consistent:
        pairs = conflicting_pairs(axioms)
        print(f"Conflicting pairs: {len(pairs)}")
        for i, (n, m) in enumerate(pairs[:10]):
            try:
                s1 = decode_statement(n)
                s2 = decode_statement(m)
                print(f"  {i+1}. [{n}] vs [{m}]")
                t1 = (getattr(s1, "text", "") or "")[:60]
                t2 = (getattr(s2, "text", "") or "")[:60]
                print(f"      \"{t1}\" vs \"{t2}\"")
            except Exception as e:
                print(f"  {i+1}. [{n}] vs [{m}] (decode error: {e})")
        if len(pairs) > 10:
            print(f"  ... and {len(pairs) - 10} more")
    else:
        print("No conflicting pairs.")


if __name__ == "__main__":
    main()
