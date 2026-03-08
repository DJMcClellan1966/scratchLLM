#!/usr/bin/env python3
"""Seed truth base with dictionary entries as BE-style statements (tier 2, category=definition)."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.sources.dictionary import load_dictionary
from base.truth_base import Statement, load_truth_base, save_truth_base


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed truth base from dictionary entries")
    ap.add_argument(
        "--dictionary",
        type=Path,
        nargs="+",
        required=True,
        help="Dictionary JSON/CSV/txt files or dirs",
    )
    ap.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output truth base JSONL path (e.g. base/truth_base.jsonl or base/dictionary_truth_base.jsonl)",
    )
    ap.add_argument(
        "--append",
        action="store_true",
        help="Append to existing truth base at --out; otherwise overwrite",
    )
    ap.add_argument(
        "--dictionary-default",
        action="store_true",
        help="Add ROOT/dictionary to dictionary paths",
    )
    args = ap.parse_args()

    paths = list(args.dictionary)
    if args.dictionary_default:
        paths.append(ROOT / "dictionary")

    docs = load_dictionary([str(p) for p in paths])
    statements: list[Statement] = []
    for d in docs:
        meta = d.meta or {}
        headword = meta.get("headword", "")
        definition = meta.get("definition", "")
        if not headword:
            continue
        text = d.text
        meaning: dict = {"type": "BE", "subj": headword, "obj": definition or "(vocabulary term)"}
        st = Statement(
            text=text,
            tier=2,
            source="dictionary",
            category="definition",
            meaning=meaning,
        )
        statements.append(st)

    if args.append and args.out.exists():
        existing = load_truth_base(args.out)
        statements = existing + statements

    save_truth_base(statements, args.out)
    print(f"Wrote {len(statements)} statement(s) to {args.out}")


if __name__ == "__main__":
    main()
