"""Unified document schema for all data sources."""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Document:
    """Single document emitted by any source. All sources use this shape."""

    text: str
    source: str  # e.g. "text_files", "email", "bookmarks", "inferred_bookmarks"
    meta: Optional[dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "source": self.source, "meta": self.meta or {}}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Document":
        return cls(
            text=d.get("text", ""),
            source=d.get("source", "unknown"),
            meta=d.get("meta") or {},
        )
