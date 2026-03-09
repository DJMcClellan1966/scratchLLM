"""
Intent-driven helper creation: guardrails, template matching, and quick corpus build.
User states what they want (e.g. "I want to junk journal") → quick corpus tailored to that intent.
"""
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Optional

from .truth_base import Statement, save_truth_base


# Default blocklist: terms that suggest illegal or immoral use. Intent is rejected if it matches.
_GUARDRAIL_BLOCKLIST = frozenset({
    "illegal", "harm", "hurt", "kill", "weapon", "exploit", "fraud", "steal",
    "cheat", "abuse", "violence", "terror", "hack", "malware", "phishing",
})


def _default_templates_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config" / "intent_templates.json"


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


def get_template_for_intent(
    intent: str,
    templates: Optional[dict[str, dict[str, Any]]] = None,
) -> Optional[str]:
    """
    Match intent to a template by keywords. Returns template_id or None (use generic).
    """
    templates = templates or load_intent_templates()
    if not templates:
        return None
    normalized = _normalize_for_match(intent)
    intent_words = set(re.findall(r"[a-z]+", normalized))
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
) -> list[Statement]:
    """Build list of Statement from template statements; optionally prepend a goal from intent."""
    out: list[Statement] = []
    if add_goal_statement and intent.strip():
        goal_text = f"Your stated goal: {intent.strip()}"
        out.append(Statement(text=goal_text, tier=2, source="user", category="intent"))
    for s in template.get("statements") or []:
        if isinstance(s, dict) and s.get("text"):
            out.append(Statement(
                text=s["text"],
                tier=int(s.get("tier", 2)),
                source=s.get("source", "curated"),
                category=s.get("category"),
            ))
    return out


def build_quick_corpus(
    intent: str,
    templates: Optional[dict[str, dict[str, Any]]] = None,
    templates_path: Optional[str | Path] = None,
    add_goal_statement: bool = True,
) -> list[Statement]:
    """
    Build a quick corpus from user intent: match a template (or generic) and optionally add a goal statement.
    """
    templates = templates or load_intent_templates(templates_path)
    template_id = get_template_for_intent(intent, templates)
    template = (templates.get(template_id) or templates.get("general")) if templates else None
    if not template:
        # No templates: minimal corpus from intent only
        st = Statement(
            text=f"Your stated goal: {intent.strip() or 'General help'}",
            tier=2,
            source="user",
            category="intent",
        )
        return [st]
    return _statements_from_template(template, intent, add_goal_statement=add_goal_statement)


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
) -> tuple[str, Path, int]:
    """
    Run guardrails, build quick corpus, save to out_dir/<id>/ and return (helper_id, truth_base_path, statement_count).
    Raises ValueError if guardrails reject the intent.
    """
    allowed, msg = check_guardrails(intent)
    if not allowed:
        raise ValueError(msg)
    statements = build_quick_corpus(intent, templates_path=templates_path)
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
        if meta_path.exists():
            try:
                with open(meta_path, encoding="utf-8") as f:
                    m = json.load(f)
                intent = m.get("intent", "")
            except Exception:
                pass
        result.append({
            "helper_id": d.name,
            "truth_base_path": str(tb),
            "intent": intent,
        })
    return result
