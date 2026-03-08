"""Formal meaning language: parse NL to structure, emit to NL, infer tier, conflict/prefer."""
import re
from dataclasses import dataclass, field
from typing import Any, Optional

# MeaningStruct: serializable dict with type and role-keyed args
MeaningStruct = dict[str, Any]


def parse_to_meaning(text: str) -> list[MeaningStruct]:
    """
    Template-based parse: "X is Y" -> BE(subj=X, obj=Y); "What is X?" -> QUERY(ref=X);
    "The X verbs Y" -> PRED. Return empty list if no pattern matches.
    """
    text = text.strip()
    if not text:
        return []
    out: list[MeaningStruct] = []
    # "What is X?" / "What's X?" / "What are X?"
    m = re.match(r"^(?:what\s+is|what's|what\s+are)\s+(.+?)\s*\??$", text, re.IGNORECASE)
    if m:
        out.append({"type": "QUERY", "ref": m.group(1).strip()})
        return out
    # "X is Y" / "X equals Y" / "X = Y"
    m = re.match(r"^(.+?)\s+(?:is|equals?|=\s*)\s*(.+?)\s*\.?$", text, re.IGNORECASE)
    if m:
        subj, obj = m.group(1).strip(), m.group(2).strip()
        if subj and obj:
            out.append({"type": "BE", "subj": subj, "obj": obj})
            return out
    # "The X verbs Y" / "X verbs Y" (e.g. Earth revolves around Sun)
    m = re.match(r"^(?:the\s+)?(.+?)\s+(\w+(?:\s+\w+)*)\s+(.+?)\s*\.?$", text, re.IGNORECASE)
    if m and not out:
        subj, pred, obj = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        if subj and pred and obj:
            out.append({"type": "PRED", "subj": subj, "pred": pred, "obj": obj})
            return out
    # Fallback: single clause "X verbs Y" (verb in middle)
    m = re.match(r"^(.+?)\s+(\w+)\s+(.+?)\s*\.?$", text)
    if m and not out:
        subj, pred, obj = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        if len(pred) <= 20 and subj and obj:
            out.append({"type": "PRED", "subj": subj, "pred": pred, "obj": obj})
    return out


def meaning_to_text(m: MeaningStruct) -> str:
    """Emit natural language from a meaning structure (inverse of parse for same subset)."""
    t = m.get("type", "")
    if t == "BE":
        return f"{m.get('subj', '')} is {m.get('obj', '')}."
    if t == "QUERY":
        return f"What is {m.get('ref', '')}?"
    if t == "PRED":
        return f"{m.get('subj', '')} {m.get('pred', '')} {m.get('obj', '')}."
    return ""


def infer_tier_from_meaning(m: MeaningStruct) -> Optional[int]:
    """
    Infer tier from structure: BE + numeric/identity -> 0; BE + geographic/scientific -> 1 or 2;
    PRED -> 2. QUERY has no tier (question).
    """
    t = m.get("type", "")
    if t == "QUERY":
        return None
    if t == "BE":
        obj = (m.get("obj") or "").strip()
        subj = (m.get("subj") or "").strip()
        if re.match(r"^[\d\s+\-*/.=]+$", subj + obj) or re.match(r"^\d+$", obj):
            return 0
        if any(
            w in (subj + " " + obj).lower()
            for w in ("capital", "country", "city", "paris", "france")
        ):
            return 2
        if any(
            w in (subj + " " + obj).lower()
            for w in ("earth", "sun", "orbit", "water", "boils", "degrees", "hour", "day")
        ):
            return 1
        return 2
    if t == "PRED":
        return 2
    return None


def conflict(s1: MeaningStruct, s2: MeaningStruct) -> bool:
    """
    True if the two meaning structs conflict: same type and same subj/ref but different obj.
    """
    t1, t2 = s1.get("type"), s2.get("type")
    if t1 != t2:
        return False
    if t1 == "BE":
        subj1 = (s1.get("subj") or "").strip().lower()
        subj2 = (s2.get("subj") or "").strip().lower()
        if subj1 != subj2:
            return False
        obj1 = (s1.get("obj") or "").strip().lower()
        obj2 = (s2.get("obj") or "").strip().lower()
        return obj1 != obj2
    if t1 == "PRED":
        subj1 = (s1.get("subj") or "").strip().lower()
        subj2 = (s2.get("subj") or "").strip().lower()
        if subj1 != subj2:
            return False
        obj1 = (s1.get("obj") or "").strip().lower()
        obj2 = (s2.get("obj") or "").strip().lower()
        return obj1 != obj2
    return False


def resolve_conflicts(
    statements_with_meanings: list[tuple[Any, Optional[MeaningStruct]]],
) -> list[Any]:
    """
    Given list of (statement, meaning), drop or prefer by tier when two conflict:
    keep the one with lower tier (more certain). Return filtered list of statements.
    Statement-like: has .tier and .text, or is a dict with "tier" and "text".
    """
    def _tier(item: Any, meaning: Optional[MeaningStruct]) -> int:
        if hasattr(item, "tier") and getattr(item, "tier", None) is not None:
            return int(getattr(item, "tier"))
        if isinstance(item, dict) and item.get("tier") is not None:
            return int(item["tier"])
        return int(infer_tier_from_meaning(meaning)) if meaning else 99

    out: list[Any] = []
    for i, (st, meaning) in enumerate(statements_with_meanings):
        tier_i = _tier(st, meaning)
        conflicted = False
        for j, (other, other_m) in enumerate(statements_with_meanings):
            if i == j or meaning is None or other_m is None:
                continue
            if not conflict(meaning, other_m):
                continue
            tier_j = _tier(other, other_m)
            if tier_j < tier_i:
                conflicted = True
                break
        if not conflicted:
            out.append(st)
    return out
