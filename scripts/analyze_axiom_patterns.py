#!/usr/bin/env python3
"""
Compute unseen patterns over IR or truth-base axioms: ambiguity per subject,
definition-use graph (in-degree), and definition templates. Output JSON for inspection.
Use --limit for quick runs; full pair-wise conflict is O(n^2) in statements with meaning.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from base.ir_bridge import load_ir_jsonl
from base.truth_base import load_truth_base
from base.language import conflict


def _subject(s) -> str:
    """Get subject from a Statement: id, meaning.subj, or first token of text."""
    subj = getattr(s, "id", None) or ((s.meaning or {}).get("subj") or "").strip()
    if subj:
        return subj
    text = (getattr(s, "text", "") or "").strip()
    if text:
        return text.split()[0][:50] if text.split() else ""
    return ""


def _definition_text(s) -> str:
    """Get definition text (statement text)."""
    return (getattr(s, "text", "") or "").strip()


def compute_ambiguity_per_subject(statements: list) -> dict[str, int]:
    """Count how many conflicting pairs each subject appears in. Only statements with meaning."""
    subjects = [_subject(s) for s in statements]
    meanings = [getattr(s, "meaning", None) for s in statements]
    conflict_count: dict[str, int] = {}
    n = len(statements)
    for i in range(n):
        if meanings[i] is None or not isinstance(meanings[i], dict):
            continue
        for j in range(i + 1, n):
            if meanings[j] is None or not isinstance(meanings[j], dict):
                continue
            if conflict(meanings[i], meanings[j]):
                a, b = subjects[i], subjects[j]
                if a:
                    conflict_count[a] = conflict_count.get(a, 0) + 1
                if b and b != a:
                    conflict_count[b] = conflict_count.get(b, 0) + 1
    return {k: v for k, v in conflict_count.items() if v > 0}


def compute_definition_use_graph(statements: list) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """Edges (from_subj, to_subj) = from is used in defining to. in_degree[subj] = how many defs use subj."""
    subjects = [_subject(s) for s in statements]
    subject_set = {s.lower() for s in subjects if s}
    edges: list[tuple[str, str]] = []
    for s in statements:
        to_subj = _subject(s)
        defn = _definition_text(s)
        if not to_subj or not defn:
            continue
        defn_lower = defn.lower()
        for other in subject_set:
            if other == to_subj.lower():
                continue
            # Whole-word/phrase match: other appears as contiguous token sequence
            pattern = r"\b" + re.escape(other).replace("\\ ", r"\s+") + r"\b"
            if re.search(pattern, defn_lower):
                edges.append((other, to_subj))
    in_degree: dict[str, int] = {}
    for from_subj, to_subj in edges:
        in_degree[from_subj] = in_degree.get(from_subj, 0) + 1
    return edges, in_degree


def compute_definition_templates(statements: list, top_k: int = 50) -> list[dict]:
    """First 30 chars (or 6 words) of each definition, normalized; return top_k by count."""
    from collections import Counter
    counter: Counter[str] = Counter()
    for s in statements:
        defn = _definition_text(s)
        if not defn:
            continue
        prefix = " ".join(defn.lower().split()[:6])[:30].strip()
        if prefix:
            counter[prefix] += 1
    return [{"prefix": p, "count": c} for p, c in counter.most_common(top_k)]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Compute ambiguity, definition-use graph, and templates over IR or truth-base."
    )
    ap.add_argument("--ir", type=Path, default=None, help="Path to IR JSONL")
    ap.add_argument("--truth-base", type=Path, default=None, help="Path to truth_base.jsonl")
    ap.add_argument("--limit", type=int, default=None, help="Max statements to load (for quick runs)")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("corpus/pattern_stats.json"),
        help="Output: .json file (single JSON) or directory (writes separate files)",
    )
    args = ap.parse_args()

    if not args.ir and not args.truth_base:
        print("Provide --ir or --truth-base.", file=sys.stderr)
        sys.exit(1)
    if args.ir and not args.ir.exists():
        print("IR file not found:", args.ir, file=sys.stderr)
        sys.exit(1)
    if args.truth_base and not args.truth_base.exists():
        print("Truth base not found:", args.truth_base, file=sys.stderr)
        sys.exit(1)

    statements: list = []
    if args.ir:
        statements = load_ir_jsonl(args.ir, limit=args.limit)
    elif args.truth_base:
        statements = load_truth_base(args.truth_base, parse_meaning_if_missing=True)
        if args.limit:
            statements = statements[: args.limit]
    if not statements:
        print("No statements loaded.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(statements)} statements.", file=sys.stderr)
    out_path = args.out.resolve()

    ambiguity = compute_ambiguity_per_subject(statements)
    edges, in_degree = compute_definition_use_graph(statements)
    templates = compute_definition_templates(statements, top_k=50)

    if out_path.suffix == ".json" and not out_path.is_dir():
        single = {
            "ambiguity_per_subject": ambiguity,
            "definition_use_in_degree": in_degree,
            "definition_templates": templates,
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(single, f, indent=2, ensure_ascii=False)
        print(f"Wrote {out_path}", file=sys.stderr)
    else:
        out_dir = out_path if out_path.is_dir() else out_path
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "ambiguity_per_subject.json", "w", encoding="utf-8") as f:
            json.dump(ambiguity, f, indent=2, ensure_ascii=False)
        with open(out_dir / "definition_use_in_degree.json", "w", encoding="utf-8") as f:
            json.dump(in_degree, f, indent=2, ensure_ascii=False)
        with open(out_dir / "definition_templates.json", "w", encoding="utf-8") as f:
            json.dump(templates, f, indent=2, ensure_ascii=False)
        with open(out_dir / "definition_use_edges.jsonl", "w", encoding="utf-8") as f:
            for a, b in edges:
                f.write(json.dumps({"from": a, "to": b}, ensure_ascii=False) + "\n")
        print(f"Wrote 4 files to {out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
