"""
Formal-only response: answer from truth base and/or IR using the formal language (meaning, tiers)
and optional Gödel IDs. No model or checkpoint required; CPU-only, local.
"""
import json
from pathlib import Path
from typing import Optional

from .truth_base import Statement, load_truth_base
from .language import resolve_conflicts
from .retrieve import retrieve_from_statements
from .ir_bridge import load_ir_jsonl
from .godel import encode_statement


def respond_formal_only(
    query: str,
    truth_base_path: Optional[str | Path] = None,
    ir_path: Optional[str | Path] = None,
    top_k: int = 5,
    max_tier: int = 2,
    resolve: bool = True,
    importance_path: Optional[str | Path] = None,
) -> tuple[str, list[int], list[Statement]]:
    """
    Answer using only the formal layer (truth base and/or IR). No model load.
    If importance_path points to a JSON with key definition_use_in_degree (e.g. from
    analyze_axiom_patterns), use it as a tie-breaker for retrieval (higher in-degree = more central).
    Returns (response_text, list of Gödel numbers of statements used, resolved statements for tier display).
    """
    statements: list[Statement] = []
    if truth_base_path:
        path = Path(truth_base_path)
        if path.exists():
            statements.extend(load_truth_base(path, parse_meaning_if_missing=True))
    if ir_path:
        path = Path(ir_path)
        if path.exists():
            statements.extend(load_ir_jsonl(path))

    if not statements:
        return ("", [], [])

    importance_map: Optional[dict[str, float]] = None
    if importance_path:
        p = Path(importance_path)
        if p.exists():
            load_path = (p / "definition_use_in_degree.json") if p.is_dir() else p
            if load_path.exists() and load_path.is_file():
                try:
                    with open(load_path, encoding="utf-8") as f:
                        data = json.load(f)
                    importance_map = data.get("definition_use_in_degree") if isinstance(data, dict) else data
                    if not isinstance(importance_map, dict):
                        importance_map = None
                except (json.JSONDecodeError, TypeError):
                    pass

    retrieved = retrieve_from_statements(
        query, statements, top_k=top_k, max_tier=max_tier, importance_map=importance_map
    )
    if not retrieved:
        return ("", [], [])

    if resolve:
        with_meanings = [(s, getattr(s, "meaning", None)) for s in retrieved]
        resolved = resolve_conflicts(with_meanings)
    else:
        resolved = retrieved

    response_text = "\n\n".join(
        (getattr(s, "text", "") or "").strip() for s in resolved if getattr(s, "text", "")
    ).strip()

    used_godel_ids: list[int] = []
    for s in resolved:
        try:
            used_godel_ids.append(encode_statement(s))
        except (TypeError, ValueError):
            pass

    return (response_text, used_godel_ids, resolved)
