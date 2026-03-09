#!/usr/bin/env python3
"""Check consistency of truth base and/or IR axioms (Gödel formal system). Exit 0 if consistent, 1 if not."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from base.formal_system import check_consistency_of_paths
from base.godel import decode_statement


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(
        description="Check Gödel consistency of truth base and/or IR. Exit 0 if consistent, 1 if not."
    )
    ap.add_argument("--truth-base", type=Path, default=None, help="Path to truth_base.jsonl")
    ap.add_argument("--ir", type=Path, default=None, help="Path to IR JSONL (e.g. pregenerated_ir.jsonl)")
    ap.add_argument("--limit", type=int, default=None, help="Use only first N lines of IR (for large files)")
    ap.add_argument("--show-pairs", type=int, default=10, help="Max conflicting pairs to print (0 = none, default 10)")
    ap.add_argument("--vertical", type=str, default=None, help="Vertical preset (e.g. general, medical, legal); uses default paths from config")
    args = ap.parse_args()

    truth_base_path = args.truth_base
    ir_path = args.ir
    if args.vertical:
        from base.vertical import resolve_vertical
        truth_base_path, ir_path, _, found = resolve_vertical(
            args.vertical, args.truth_base, args.ir, None, ROOT
        )
        if not found:
            print(f"Unknown vertical: {args.vertical}. Using explicit paths only.", file=sys.stderr)

    if not truth_base_path and not ir_path:
        print("Provide at least one of --truth-base or --ir (or use --vertical with a preset that has defaults).", file=sys.stderr)
        sys.exit(2)
    if truth_base_path and not Path(truth_base_path).exists():
        print("Truth base not found:", truth_base_path, file=sys.stderr)
        sys.exit(2)
    if ir_path and not Path(ir_path).exists():
        print("IR file not found:", ir_path, file=sys.stderr)
        sys.exit(2)

    consistent, pairs = check_consistency_of_paths(
        truth_base_path=truth_base_path,
        ir_path=ir_path,
        ir_limit=args.limit,
    )

    if consistent:
        print("Consistent: yes")
        sys.exit(0)
    print("Consistent: no")
    print(f"Conflicting pairs: {len(pairs)}")
    if args.show_pairs > 0 and pairs:
        for i, (n, m) in enumerate(pairs[: args.show_pairs]):
            try:
                st_n = decode_statement(n)
                st_m = decode_statement(m)
                text_n = (getattr(st_n, "text", "") or "")[:100]
                text_m = (getattr(st_m, "text", "") or "")[:100]
                print(f"  [{i+1}] IDs {n} vs {m}")
                print(f"      \"{text_n}...\" vs \"{text_m}...\"")
            except Exception:
                print(f"  [{i+1}] IDs {n} vs {m}")
        if len(pairs) > args.show_pairs:
            print(f"  ... and {len(pairs) - args.show_pairs} more")
    sys.exit(1)


if __name__ == "__main__":
    main()
