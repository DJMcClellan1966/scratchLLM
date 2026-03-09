#!/usr/bin/env python3
"""Respond using only the formal layer (truth base and/or IR). No checkpoint; CPU-only."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _safe_print(s: str) -> None:
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(s, flush=True)
    except (UnicodeEncodeError, UnicodeError):
        sys.stdout.buffer.write(s.encode(enc, errors="replace") + b"\n")
        sys.stdout.buffer.flush()


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(
        description="Fast response from truth base and/or IR (no model). Formal language + Gödel; local/CPU."
    )
    ap.add_argument("--query", type=str, required=True, help="Question or lookup (e.g. 'What is X?')")
    ap.add_argument("--truth-base", type=Path, default=None, help="Path to truth_base.jsonl")
    ap.add_argument("--ir", type=Path, default=None, help="Path to IR JSONL (e.g. pregenerated_ir.jsonl)")
    ap.add_argument("--top-k", type=int, default=5, help="Max statements to use")
    ap.add_argument("--max-tier", type=int, default=2, help="Max tier (0–2) for retrieval; lower = stricter")
    ap.add_argument("--no-resolve", action="store_true", help="Skip conflict resolution")
    ap.add_argument("--show-ids", action="store_true", help="Print Gödel numbers of statements used")
    ap.add_argument("--show-tiers", action="store_true", help="Print each statement with its tier label")
    ap.add_argument("--check-consistency", action="store_true", help="Warn if truth base/IR is inconsistent before responding")
    ap.add_argument("--limit", type=int, default=None, help="Use only first N lines of IR (for consistency check on large files)")
    ap.add_argument("--importance", type=Path, default=None, help="Path to pattern_stats.json (or dir with definition_use_in_degree) for tie-break ranking")
    ap.add_argument("--vertical", type=str, default=None, help="Vertical preset (e.g. general, medical, legal); uses default paths and max_tier from config")
    ap.add_argument("--format", choices=["text", "json"], default="text", help="Output format: text or json (for integration)")
    ap.add_argument("--audit", action="store_true", help="Include audit blob (citations, tiers, consistency); use with --format json or print summary")
    ap.add_argument("--output", type=Path, default=None, help="Write JSON output to file (when --format json)")
    args = ap.parse_args()

    truth_base_path = args.truth_base
    ir_path = args.ir
    max_tier = args.max_tier
    if args.vertical:
        from base.vertical import load_verticals_config, get_vertical, resolve_paths
        config = load_verticals_config()
        vertical = get_vertical(config, args.vertical)
        if vertical:
            truth_base_path, ir_path, max_tier = resolve_paths(
                vertical,
                truth_base_override=args.truth_base,
                ir_override=args.ir,
                max_tier_override=args.max_tier,
                base_dir=ROOT,
            )
        else:
            print(f"Unknown vertical: {args.vertical}. Using explicit paths only.", file=sys.stderr)

    if not truth_base_path and not ir_path:
        print("Provide at least one of --truth-base or --ir (or use --vertical with a preset that has defaults).", file=sys.stderr)
        sys.exit(1)
    if truth_base_path and not Path(truth_base_path).exists():
        print("Truth base not found:", truth_base_path, file=sys.stderr)
        sys.exit(1)
    if ir_path and not Path(ir_path).exists():
        print("IR file not found:", ir_path, file=sys.stderr)
        sys.exit(1)

    from base import respond_formal_only, check_consistency_of_paths
    import json as _json

    use_audit = args.audit or args.format == "json"
    if args.check_consistency and not use_audit:
        consistent, pairs = check_consistency_of_paths(
            truth_base_path=truth_base_path,
            ir_path=ir_path,
            ir_limit=args.limit,
        )
        if not consistent:
            print(f"Warning: truth base/IR inconsistent ({len(pairs)} conflicting pair(s)). Proceeding anyway.", file=sys.stderr)

    result = respond_formal_only(
        args.query,
        truth_base_path=truth_base_path,
        ir_path=ir_path,
        top_k=args.top_k,
        max_tier=max_tier,
        resolve=not args.no_resolve,
        importance_path=args.importance,
        include_audit=use_audit,
        run_consistency_check=use_audit or args.check_consistency,
        vertical_id=args.vertical,
        ir_limit=args.limit,
    )
    response_text = result[0]
    used_godel_ids = result[1]
    resolved_statements = result[2] if len(result) > 2 else []
    audit = result[3] if len(result) > 3 else None

    if args.format == "json":
        out = {
            "response": response_text or "(no matching statements)",
            "citation_ids": used_godel_ids,
            "tiers": [getattr(s, "tier", None) for s in resolved_statements],
            "audit": audit,
        }
        j = _json.dumps(out, ensure_ascii=False, indent=2 if args.output else None)
        if args.output:
            args.output.write_text(j, encoding="utf-8")
        else:
            _safe_print(j)
        return

    _safe_print(response_text or "(no matching statements)")
    if args.show_tiers and resolved_statements:
        _safe_print("")
        for s in resolved_statements:
            tier_name = getattr(s, "tier", None)
            text = (getattr(s, "text", "") or "")[:200]
            _safe_print(f"[Tier {tier_name}] {text}" + ("..." if len((getattr(s, "text", "") or "")) > 200 else ""))
    if args.show_ids and used_godel_ids:
        _safe_print("")
        _safe_print("Gödel IDs: " + ", ".join(str(n) for n in used_godel_ids))
    if args.audit and audit:
        _safe_print("")
        _safe_print("Audit: {} citations, consistency: {}".format(
            len(used_godel_ids),
            "yes" if audit.get("consistent") is True else ("no" if audit.get("consistent") is False else "not checked"),
        ))


if __name__ == "__main__":
    main()
