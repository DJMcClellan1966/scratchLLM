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
    """Return top-k statement texts from truth base (tier <= max_tier) by word overlap with query."""
    statements = load_truth_base(truth_base_path)
    statements = [s for s in statements if s.tier <= max_tier]
    if not statements:
        return []
    q_words = _word_set(query)
    scored = []
    for s in statements:
        s_words = _word_set(s.text)
        overlap = len(q_words & s_words) if q_words else 0
        scored.append((overlap, -s.tier, s.text))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [t for _, _, t in scored[:top_k]]


def retrieve_truth_base_by_meaning(
    query: str,
    truth_base_path: str | Path,
    top_k: int = 5,
    max_tier: int = 2,
) -> list[Statement]:
    """Return top-k Statements (with meaning) by meaning overlap; fallback to word overlap."""
    statements = load_truth_base(truth_base_path, parse_meaning_if_missing=True)
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
        if m_score > 0:
            scored.append((m_score, overlap, -s.tier, s))
        else:
            scored.append((0, overlap, -s.tier, s))
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return [s for _, _, _, s in scored[:top_k]]


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
) -> tuple[list[str], list[str]]:
    """Return (truth_chunks, corpus_chunks). If use_meaning, retrieve by meaning and optionally resolve conflicts."""
    truth_chunks: list[str] = []
    corpus_chunks: list[str] = []
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
            else:
                truth_chunks = [s.text for s in statements]
        else:
            truth_chunks = retrieve_truth_base(
                prompt, truth_base_path, top_k=truth_top_k, max_tier=max_tier_truth
            )
    if corpus_path:
        corpus_chunks = retrieve_corpus(
            prompt, corpus_path, top_k=corpus_top_k, max_tier=max_tier_corpus
        )
    return (truth_chunks, corpus_chunks)
