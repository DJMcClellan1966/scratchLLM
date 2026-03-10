"""
Intent-driven helper creation: guardrails, template matching, and quick corpus build.
User states what they want (e.g. "I want to junk journal") → quick corpus tailored to that intent.
"""
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Optional

from .truth_base import Statement, load_truth_base, save_truth_base
from .ir_bridge import load_ir_jsonl


# Default blocklist: terms that suggest illegal or immoral use. Intent is rejected if it matches.
_GUARDRAIL_BLOCKLIST = frozenset({
    "illegal", "harm", "hurt", "kill", "weapon", "exploit", "fraud", "steal",
    "cheat", "abuse", "violence", "terror", "hack", "malware", "phishing",
})


def _default_templates_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config" / "intent_templates.json"


def _default_onboarding_terms_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config" / "onboarding_terms.json"


def get_onboarding_definitions(
    template_id: Optional[str],
    base_dir: Optional[Path] = None,
    ir_path: Optional[str | Path] = None,
    max_definitions: int = 3,
) -> list[tuple[str, str]]:
    """
    Return up to max_definitions (term, definition) for the given template_id for use in onboarding.
    Loads config/onboarding_terms.json for term list and scans IR JSONL (subject, definition) for matches.
    """
    base_dir = base_dir or Path(__file__).resolve().parent.parent
    terms_path = _default_onboarding_terms_path()
    if not terms_path.exists():
        return []
    try:
        with open(terms_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, dict) or not template_id:
        return []
    terms = data.get(template_id)
    if not isinstance(terms, list):
        return []
    terms_lower = [t.lower() for t in terms if isinstance(t, str)]
    if not terms_lower:
        return []
    path = Path(ir_path) if ir_path else base_dir / "corpus" / "rag_ir.jsonl"
    if not path.exists():
        return []
    result: list[tuple[str, str]] = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if len(result) >= max_definitions:
                    break
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                subj = (rec.get("subject") or "").strip().lower()
                if subj not in terms_lower:
                    continue
                defin = (rec.get("definition") or "").strip()[:200]
                result.append((rec.get("subject", subj), defin))
    except (json.JSONDecodeError, OSError):
        pass
    return result[:max_definitions]


def load_intent_templates(path: Optional[str | Path] = None) -> dict[str, dict[str, Any]]:
    """
    Load intent templates from JSON. Returns dict template_id -> {id, label, keywords, statements}.
    """
    p = Path(path) if path else _default_templates_path()
    if not p.exists():
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, dict) and "statements" in v}


def check_guardrails(
    intent: str,
    blocklist: Optional[frozenset[str]] = None,
) -> tuple[bool, str]:
    """
    Check if the intent is allowed (legal, moral). Returns (allowed, message).
    """
    blocklist = blocklist or _GUARDRAIL_BLOCKLIST
    normalized = _normalize_for_match(intent)
    words = set(re.findall(r"[a-z]+", normalized))
    for bad in blocklist:
        if bad in words or bad in normalized:
            return (False, "That request cannot be supported. Please describe a different kind of help.")
    return (True, "OK")


def _normalize_for_match(text: str) -> str:
    """Lowercase, collapse whitespace, basic ASCII fold."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text.strip().lower())
    text = re.sub(r"\s+", " ", text)
    return text


# Strong terms: if intent contains any of these, prefer this template over others (avoids e.g. "journal" matching when user said "bible reading").
_TEMPLATE_PRIORITY_TERMS: dict[str, list[str]] = {
    "bible_daily": ["bible", "scripture", "devotional", "bible reading", "read the bible"],
}


def get_template_for_intent(
    intent: str,
    templates: Optional[dict[str, dict[str, Any]]] = None,
) -> Optional[str]:
    """
    Match intent to a template by keywords. Returns template_id or None (use generic).
    When intent contains priority terms for a template (e.g. "bible"), that template wins.
    """
    templates = templates or load_intent_templates()
    if not templates:
        return None
    normalized = _normalize_for_match(intent)
    intent_words = set(re.findall(r"[a-z]+", normalized))
    for tid, terms in _TEMPLATE_PRIORITY_TERMS.items():
        if tid not in templates:
            continue
        if any(term in normalized or all(w in intent_words for w in term.split()) for term in terms):
            return tid
    best_id: Optional[str] = None
    best_score = 0
    for tid, t in templates.items():
        keywords = t.get("keywords") or []
        if not keywords:
            continue
        score = sum(1 for kw in keywords if kw in normalized or any(w in intent_words for w in kw.split()))
        if score > best_score:
            best_score = score
            best_id = tid
    return best_id if best_id else (None if "general" not in templates else "general")


def _statements_from_template(
    template: dict[str, Any],
    intent: str,
    add_goal_statement: bool = True,
    experience_level: Optional[str] = None,
) -> list[Statement]:
    """Build list of Statement from template statements; optionally prepend a goal; filter by experience_level if set."""
    out: list[Statement] = []
    if add_goal_statement and intent.strip():
        goal_text = f"Your stated goal: {intent.strip()}"
        if experience_level:
            goal_text += f" You're at {experience_level} level."
        out.append(Statement(text=goal_text, tier=2, source="user", category="intent"))
    for s in template.get("statements") or []:
        if not isinstance(s, dict) or not s.get("text"):
            continue
        stmt_level = s.get("level")
        stmt_levels = s.get("levels")
        if experience_level and (stmt_level or stmt_levels):
            if stmt_level and stmt_level != experience_level:
                continue
            if stmt_levels and experience_level not in stmt_levels:
                continue
        out.append(Statement(
            text=s["text"],
            tier=int(s.get("tier", 2)),
            source=s.get("source", "curated"),
            category=s.get("category"),
        ))
    return out


def _load_merge_statements(
    path: str | Path,
    base_dir: Optional[Path] = None,
    limit: int = 500,
) -> list[Statement]:
    """Load statements from a truth base or IR JSONL path; return up to limit."""
    base_dir = base_dir or Path(__file__).resolve().parent.parent
    resolved = base_dir / path if not Path(str(path)).is_absolute() else Path(path)
    if not resolved.exists():
        return []
    out: list[Statement] = []
    if resolved.suffix == ".jsonl":
        with open(resolved, encoding="utf-8") as f:
            first_line = f.readline()
        try:
            first = json.loads(first_line) if first_line.strip() else {}
        except json.JSONDecodeError:
            first = {}
        if "subject" in first or "definition" in first:
            out = load_ir_jsonl(resolved)
        else:
            out = load_truth_base(resolved, parse_meaning_if_missing=False)
    if limit and len(out) > limit:
        out = out[:limit]
    return out


def build_quick_corpus(
    intent: str,
    templates: Optional[dict[str, dict[str, Any]]] = None,
    templates_path: Optional[str | Path] = None,
    add_goal_statement: bool = True,
    base_dir: Optional[Path] = None,
    blank_canvas: bool = False,
    experience_level: Optional[str] = None,
    needs_vocabulary: bool = False,
) -> list[Statement]:
    """
    Build a quick corpus from user intent. If blank_canvas is True, return only the user's goal
    statement (no template, no merge) so the app is a blank canvas built from their input over time.
    Otherwise match a template (or generic), add goal statement, filter by experience_level if set,
    and optional merge_ir / merge_truth_base (and dictionary when needs_vocabulary).
    """
    goal_text = f"Your stated goal: {intent.strip() or 'General help'}."
    if experience_level:
        goal_text += f" You're at {experience_level} level."
    goal_only = Statement(text=goal_text, tier=2, source="user", category="intent")
    if blank_canvas:
        return [goal_only]
    templates = templates or load_intent_templates(templates_path)
    template_id = get_template_for_intent(intent, templates)
    template = (templates.get(template_id) or templates.get("general")) if templates else None
    if not template:
        return [goal_only]
    statements = _statements_from_template(
        template, intent, add_goal_statement=add_goal_statement, experience_level=experience_level
    )
    merge_limit = int(template.get("merge_limit", 500))
    for key in ("merge_truth_base", "merge_ir"):
        path = template.get(key)
        if path and isinstance(path, str):
            extra = _load_merge_statements(path, base_dir=base_dir, limit=merge_limit)
            statements.extend(extra)
    if needs_vocabulary and not (template.get("merge_ir") or template.get("merge_truth_base")):
        dict_path = "corpus/rag_ir.jsonl"
        vocab_limit = min(merge_limit, 300)
        extra = _load_merge_statements(dict_path, base_dir=base_dir, limit=vocab_limit)
        statements.extend(extra)
    return statements


def _slug_from_intent(intent: str, max_len: int = 40) -> str:
    """Produce a filesystem-safe slug from intent."""
    s = _normalize_for_match(intent)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    if not s:
        s = "helper"
    return s[:max_len] if len(s) > max_len else s


def create_helper_from_intent(
    intent: str,
    out_dir: str | Path,
    templates_path: Optional[str | Path] = None,
    helper_id: Optional[str] = None,
    base_dir: Optional[Path] = None,
    blank_canvas: bool = False,
    experience_level: Optional[str] = None,
    needs_vocabulary: bool = False,
) -> tuple[str, Path, int]:
    """
    Run guardrails, build quick corpus, save to out_dir/<id>/ and return (helper_id, truth_base_path, statement_count).
    Raises ValueError if guardrails reject the intent.
    If blank_canvas is True, the helper contains only the user's goal (no template content); the app is a blank canvas.
    Otherwise templates may specify merge_ir or merge_truth_base to merge in dictionary/IR content.
    experience_level: "beginner" | "some_experience" | "advanced" (optional, for onboarding).
    needs_vocabulary: if True, merge dictionary/IR for definitions when building corpus (when not blank_canvas).
    """
    allowed, msg = check_guardrails(intent)
    if not allowed:
        raise ValueError(msg)
    base_dir = base_dir or Path(__file__).resolve().parent.parent
    statements = build_quick_corpus(
        intent,
        templates_path=templates_path,
        base_dir=base_dir,
        blank_canvas=blank_canvas,
        experience_level=experience_level,
        needs_vocabulary=needs_vocabulary,
    )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = helper_id or _slug_from_intent(intent)
    # Ensure unique dir if same slug exists (e.g. append _1, _2)
    base_slug = slug
    idx = 0
    while (out_dir / slug).exists():
        idx += 1
        slug = f"{base_slug}_{idx}"
    helper_dir = out_dir / slug
    helper_dir.mkdir(parents=True, exist_ok=True)
    truth_base_path = helper_dir / "truth_base.jsonl"
    save_truth_base(statements, truth_base_path, check_consistency=False)
    meta = {
        "intent": intent.strip(),
        "helper_id": slug,
        "statement_count": len(statements),
    }
    if experience_level is not None:
        meta["experience_level"] = experience_level
    if needs_vocabulary:
        meta["needs_vocabulary"] = True
    meta_path = helper_dir / "meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return (slug, truth_base_path, len(statements))


def list_user_helpers(out_dir: str | Path) -> list[dict[str, Any]]:
    """
    List helpers in out_dir: each has helper_id, path to truth_base, intent from meta if present.
    """
    out_dir = Path(out_dir)
    if not out_dir.is_dir():
        return []
    result = []
    for d in sorted(out_dir.iterdir()):
        if not d.is_dir():
            continue
        tb = d / "truth_base.jsonl"
        if not tb.exists():
            continue
        meta_path = d / "meta.json"
        intent = ""
        experience_level = None
        needs_vocabulary = False
        if meta_path.exists():
            try:
                with open(meta_path, encoding="utf-8") as f:
                    m = json.load(f)
                intent = m.get("intent", "")
                experience_level = m.get("experience_level")
                needs_vocabulary = m.get("needs_vocabulary", False)
            except Exception:
                pass
        result.append({
            "helper_id": d.name,
            "truth_base_path": str(tb),
            "intent": intent,
            "experience_level": experience_level,
            "needs_vocabulary": needs_vocabulary,
        })
    return result
