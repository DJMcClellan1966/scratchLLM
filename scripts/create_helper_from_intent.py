#!/usr/bin/env python3
"""Create a user helper from free-text intent. Guardrails apply; quick corpus is built from templates or generic."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a helper from intent (e.g. 'I want to junk journal'). Saves truth base to corpus/user_helpers/<id>/."
    )
    parser.add_argument(
        "intent",
        nargs="?",
        default="",
        help="What you want help with (e.g. 'I want to junk journal' or 'I am going on a hike here').",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "corpus" / "user_helpers",
        help="Directory to store user helpers (default: corpus/user_helpers).",
    )
    parser.add_argument(
        "--templates",
        type=Path,
        default=None,
        help="Path to intent_templates.json (default: config/intent_templates.json).",
    )
    parser.add_argument(
        "--id",
        dest="helper_id",
        type=str,
        default=None,
        help="Optional helper id/slug (default: derived from intent).",
    )
    args = parser.parse_args()
    intent = (args.intent or "").strip()
    if not intent:
        print("Usage: python create_helper_from_intent.py \"I want to junk journal\"", file=sys.stderr)
        print("   or: python create_helper_from_intent.py --help", file=sys.stderr)
        sys.exit(1)
    try:
        from base.intent import create_helper_from_intent
        helper_id, truth_base_path, count = create_helper_from_intent(
            intent,
            out_dir=args.out_dir,
            templates_path=args.templates,
            helper_id=args.helper_id,
        )
        print(f"Created helper: {helper_id}")
        print(f"Truth base: {truth_base_path}")
        print(f"Statements: {count}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
