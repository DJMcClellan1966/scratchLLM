#!/usr/bin/env python3
"""Generate a compliance report: KB consistency, axiom count, tier breakdown. For auditors."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(
        description="Generate compliance report: consistency, axiom count, tier breakdown."
    )
    ap.add_argument("--vertical", type=str, default=None, help="Vertical preset (e.g. medical, legal, compliance)")
    ap.add_argument("--truth-base", type=Path, default=None, help="Path to truth_base.jsonl")
    ap.add_argument("--ir", type=Path, default=None, help="Path to IR JSONL")
    ap.add_argument("--ir-limit", type=int, default=None, help="Use only first N lines of IR")
    ap.add_argument("--output", type=Path, default=None, help="Write report to file (default: stdout for json, or compliance_report_YYYYMMDD.json)")
    ap.add_argument("--format", choices=["json", "text"], default="json", help="Report format: json or text")
    args = ap.parse_args()

    truth_base_path = args.truth_base
    ir_path = args.ir
    vertical_id = args.vertical
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

    from base.formal_system import check_consistency_of_paths
    from base.truth_base import load_truth_base
    from base.ir_bridge import load_ir_jsonl

    consistent, pairs = check_consistency_of_paths(
        truth_base_path=truth_base_path,
        ir_path=ir_path,
        ir_limit=args.ir_limit,
    )
    conflicting_pairs_count = len(pairs)

    statements = []
    if truth_base_path and Path(truth_base_path).exists():
        statements.extend(load_truth_base(truth_base_path, parse_meaning_if_missing=False))
    if ir_path and Path(ir_path).exists():
        statements.extend(load_ir_jsonl(ir_path, limit=args.ir_limit))
    axiom_count = len(statements)

    tier_breakdown: dict[str, int] = {}
    for s in statements:
        t = getattr(s, "tier", None)
        key = str(t) if t is not None else "unknown"
        tier_breakdown[key] = tier_breakdown.get(key, 0) + 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "vertical_id": vertical_id,
        "truth_base_path": str(truth_base_path) if truth_base_path else None,
        "ir_path": str(ir_path) if ir_path else None,
        "consistency": {
            "consistent": consistent,
            "conflicting_pairs_count": conflicting_pairs_count,
        },
        "axiom_count": axiom_count,
        "tier_breakdown": tier_breakdown,
    }

    if args.format == "json":
        j = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(j, encoding="utf-8")
            print(f"Report written to {args.output}", file=sys.stderr)
        else:
            print(j)
    else:
        lines = [
            f"Compliance report — {report['generated_at']}",
            f"Vertical: {vertical_id or 'none'}",
            f"Truth base: {report['truth_base_path']}",
            f"IR: {report['ir_path']}",
            "",
            f"Consistency: {'yes' if consistent else 'no'} (conflicting pairs: {conflicting_pairs_count})",
            f"Axiom count: {axiom_count}",
            "Tier breakdown: " + ", ".join(f"{k}={v}" for k, v in sorted(tier_breakdown.items())),
        ]
        text = "\n".join(lines)
        if args.output:
            args.output.write_text(text, encoding="utf-8")
            print(f"Report written to {args.output}", file=sys.stderr)
        else:
            print(text)


if __name__ == "__main__":
    main()
