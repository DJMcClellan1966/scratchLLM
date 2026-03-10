"""
Append user notes and outcomes to a helper's truth base so the assistant learns over time.
Used by the Niche Personalizer: "Remember this", "Record outcome", etc.
"""
from pathlib import Path
from typing import Union

from .truth_base import Statement, load_truth_base, save_truth_base


def append_to_truth_base(
    truth_base_path: Union[str, Path],
    new_statements: list[Statement],
    check_consistency: bool = False,
) -> None:
    """
    Load existing truth base, append new_statements, save.
    Creates file and parent dir if path does not exist.
    """
    path = Path(truth_base_path)
    existing = load_truth_base(path) if path.exists() else []
    combined = existing + list(new_statements)
    save_truth_base(combined, path, check_consistency=check_consistency)


def statements_from_user_note(
    note: str,
    category: str = "user_note",
) -> list[Statement]:
    """Build one Statement from a user note (e.g. 'Remember this')."""
    text = (note or "").strip()
    if not text:
        return []
    return [
        Statement(
            text=text,
            tier=2,
            source="user",
            category=category,
        )
    ]


def statements_from_outcome(
    experiment_description: str,
    result: str,
    notes: str = "",
    category: str = "outcome",
) -> list[Statement]:
    """
    Build one or two Statements from an experiment outcome.
    First: "Experiment: [desc]. Result: [result]. [notes]."
    Optional second: short lesson line for retrieval if notes present.
    """
    desc = (experiment_description or "").strip()
    result = (result or "").strip().lower()
    if result not in ("success", "failure", "skipped"):
        result = "noted"
    notes = (notes or "").strip()
    if not desc:
        return []
    parts = [f"Experiment: {desc}. Result: {result}."]
    if notes:
        parts.append(notes)
    text = " ".join(parts)
    out = [
        Statement(
            text=text,
            tier=2,
            source="user",
            category=category,
        )
    ]
    if notes and len(notes) < 120:
        out.append(
            Statement(
                text=notes,
                tier=2,
                source="user",
                category=category,
            )
        )
    return out
