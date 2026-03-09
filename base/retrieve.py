"""Retrieve from truth base and tiered corpus by query (keyword/overlap or meaning)."""
from pathlib import Path
from typing import Optional

from .truth_base import Statement, load_truth_base
from .language import parse_to_meaning

# Corpus docs: use data.schema.Document when available
try:
    from data.corpus import load_corpus_jsonl
    from data.schema import Document
except ImportError:
    load_corpus_jsonl = None
    Document = None


def _word_set(text: str) -> set[str]:
    """Lowercase words for overlap scoring."""
    return set(w.lower() for w in text.split() if w.isalnum() or w.strip())


def _meaning_score(query_meaning: dict, statement_meaning: dict) -> int:
    """Score 0-3 by overlap: same ref/subj/obj, same type, etc."""
    if not query_meaning or not statement_meaning:
        return 0
    tq, ts = query_meaning.get("type"), statement_meaning.get("type")
    if tq != ts:
        return 0
    score = 1
    if tq == "QUERY":
        ref_q = (query_meaning.get("ref") or "").lower()
        ref_s = (statement_meaning.get("ref") or statement_meaning.get("subj") or "").lower()
        if ref_q in ref_s or ref_s in ref_q:
            score = 2
        for key in ("subj", "obj"):
            if ref_q in (statement_meaning.get(key) or "").lower():
                score = 2
    else:
        subj_q = (query_meaning.get("subj") or "").lower()
        obj_q = (query_meaning.get("obj") or "").lower()
        subj_s = (statement_meaning.get("subj") or "").lower()
        obj_s = (statement_meaning.get("obj") or "").lower()
        if subj_q and subj_q in subj_s:
            score += 1
        if obj_q and obj_q in obj_s:
            score += 1
    return min(score, 3)


def retrieve_truth_base(
    query: str,
    truth_base_path: str | Path,
    top_k: int = 5,
    max_tier: int = 2,
) -> list[str]:
    """Return top-k statement texts (tier <= max_tier) by word overlap; tie-break by shorter text."""
    statements = load_truth_base(truth_base_path)
    statements = [s for s in statements if s.tier <= max_tier]
    if not statements:
        return []
    q_words = _word_set(query)
    scored = []
    for s in statements:
        s_words = _word_set(s.text)
        overlap = len(q_words & s_words) if q_words else 0
        simplicity = -len(s.text)
        scored.append((overlap, -s.tier, simplicity, s.text))
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return [t for _, _, _, t in scored[:top_k]]


def _subject_for_importance(s: Statement) -> str:
    """Subject for importance lookups: id, meaning.subj, or empty."""
    subj = getattr(s, "id", None) or ((getattr(s, "meaning", None) or {}).get("subj") or "")
    return (subj or "").strip()


def retrieve_from_statements(
    query: str,
    statements: list[Statement],
    top_k: int = 5,
    max_tier: int = 2,
    importance_map: Optional[dict[str, float]] = None,
) -> list[Statement]:
    """
    Return top-k Statements by meaning overlap, word overlap, tier; tie-break by simplicity (shorter text)
    and optionally importance (e.g. from pattern_stats definition_use_in_degree).
    """
    statements = [s for s in statements if s.tier <= max_tier]
    if not statements:
        return []
    q_meanings = parse_to_meaning(query)
    q_meaning = q_meanings[0] if q_meanings else None
    q_words = _word_set(query)
    scored = []
    for s in statements:
        m_score = _meaning_score(q_meaning, s.meaning) if (q_meaning and s.meaning) else 0
        overlap = len(q_words & _word_set(s.text)) if q_words else 0
        simplicity = -len((getattr(s, "text", "") or ""))  # prefer shorter (Kolmogorov-style tie-break)
        subj = _subject_for_importance(s)
        importance = (importance_map or {}).get(subj.lower(), 0.0) if importance_map else 0.0
        scored.append((m_score, overlap, -s.tier, simplicity, importance, s))
    scored.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4]), reverse=True)
    return [s for _, _, _, _, _, s in scored[:top_k]]


def retrieve_truth_base_by_meaning(
    query: str,
    truth_base_path: str | Path,
    top_k: int = 5,
    max_tier: int = 2,
    importance_map: Optional[dict[str, float]] = None,
) -> list[Statement]:
    """Return top-k Statements (with meaning) by meaning overlap; tie-break by simplicity and optional importance."""
    statements = load_truth_base(truth_base_path, parse_meaning_if_missing=True)
    return retrieve_from_statements(
        query, statements, top_k=top_k, max_tier=max_tier, importance_map=importance_map
    )


def retrieve_corpus(
    query: str,
    corpus_path: str | Path,
    top_k: int = 5,
    max_tier: Optional[int] = None,
) -> list[str]:
    """Return top-k document texts from corpus.jsonl by word overlap; optional filter by tier."""
    if load_corpus_jsonl is None or Document is None:
        return []
    corpus_path = Path(corpus_path)
    if not corpus_path.exists():
        return []
    docs = load_corpus_jsonl(corpus_path)
    if max_tier is not None:
        docs = [d for d in docs if (d.meta or {}).get("tier", 99) <= max_tier]
    if not docs:
        return []
    q_words = _word_set(query)
    scored = []
    for d in docs:
        t = getattr(d, "text", "") or ""
        s_words = _word_set(t)
        overlap = len(q_words & s_words) if q_words else 0
        tier = (d.meta or {}).get("tier", 99)
        scored.append((overlap, -tier, t[:2000]))  # cap length
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [t for _, _, t in scored[:top_k]]


def retrieve_for_prompt(
    prompt: str,
    truth_base_path: Optional[str | Path] = None,
    corpus_path: Optional[str | Path] = None,
    truth_top_k: int = 5,
    corpus_top_k: int = 5,
    max_tier_truth: int = 2,
    max_tier_corpus: Optional[int] = 6,
    use_meaning: bool = False,
    resolve: bool = True,
    return_truth_statements: bool = False,
) -> tuple[list[str], list[str]] | tuple[list[str], list[str], list[Statement]]:
    """
    Return (truth_chunks, corpus_chunks). If use_meaning, retrieve by meaning and optionally resolve conflicts.
    If return_truth_statements is True, return (truth_chunks, corpus_chunks, truth_statements) where
    truth_statements are the Statement objects used for truth_chunks (non-empty only when use_meaning=True).
    """
    truth_chunks: list[str] = []
    corpus_chunks: list[str] = []
    truth_statements: list[Statement] = []
    if truth_base_path:
        if use_meaning:
            statements = retrieve_truth_base_by_meaning(
                prompt, truth_base_path, top_k=truth_top_k, max_tier=max_tier_truth
            )
            if resolve and statements:
                from .language import resolve_conflicts
                with_meanings = [(s, s.meaning) for s in statements]
                resolved = resolve_conflicts(with_meanings)
                truth_chunks = [s.text if hasattr(s, "text") else str(s) for s in resolved]
                truth_statements = list(resolved)
            else:
                truth_chunks = [s.text for s in statements]
                truth_statements = list(statements)
        else:
            truth_chunks = retrieve_truth_base(
                prompt, truth_base_path, top_k=truth_top_k, max_tier=max_tier_truth
            )
    if corpus_path:
        corpus_chunks = retrieve_corpus(
            prompt, corpus_path, top_k=corpus_top_k, max_tier=max_tier_corpus
        )
    if return_truth_statements:
        return (truth_chunks, corpus_chunks, truth_statements)
    return (truth_chunks, corpus_chunks)
