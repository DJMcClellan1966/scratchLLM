"""Truth base store: load/save tier 0-2 statements (necessary, empirical, contingent)."""
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from .tiers import Tier

# MeaningStruct from language (avoid circular import at module load)
MeaningStruct = dict[str, Any]


@dataclass
class Statement:
    """Single statement in the truth base. text, tier, optional source/category/id/meaning."""

    text: str
    tier: int  # 0, 1, or 2 for truth base
    source: str = "curated"
    category: Optional[str] = None  # e.g. "math", "science"
    id: Optional[str] = field(default=None)
    meaning: Optional[MeaningStruct] = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        d = {"text": self.text, "tier": self.tier, "source": self.source}
        if self.category is not None:
            d["category"] = self.category
        if self.id is not None:
            d["id"] = self.id
        if self.meaning is not None:
            d["meaning"] = self.meaning
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Statement":
        return cls(
            text=d.get("text", ""),
            tier=int(d.get("tier", 0)),
            source=d.get("source", "curated"),
            category=d.get("category"),
            id=d.get("id"),
            meaning=d.get("meaning"),
        )


def load_truth_base(
    path: str | Path,
    parse_meaning_if_missing: bool = False,
) -> list[Statement]:
    """Load truth base from JSONL. If parse_meaning_if_missing, compute meaning from text when absent."""
    path = Path(path)
    if not path.exists():
        return []
    statements: list[Statement] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            st = Statement.from_dict(json.loads(line))
            if st.meaning is None and parse_meaning_if_missing:
                try:
                    from .language import parse_to_meaning
                    parsed = parse_to_meaning(st.text)
                    if parsed:
                        st.meaning = parsed[0]
                except Exception:
                    pass
            statements.append(st)
    return statements


def save_truth_base(
    statements: list[Statement],
    path: str | Path,
    check_consistency: bool = False,
) -> None:
    """
    Save truth base to JSONL.
    If check_consistency is True, run formal-system consistency on the statement set
    before writing; if inconsistent, raise ValueError with conflicting pair count and pairs.
    """
    if check_consistency and statements:
        from .godel import encode_statement
        from .formal_system import is_consistent, conflicting_pairs
        axioms = {encode_statement(s) for s in statements}
        if not is_consistent(axioms):
            pairs = conflicting_pairs(axioms)
            err = ValueError(
                f"Truth base inconsistent: {len(pairs)} conflicting pair(s). "
                "Resolve conflicts or save without check_consistency."
            )
            err.conflicting_pairs = pairs  # type: ignore[attr-defined]
            raise err
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for s in statements:
            f.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")
