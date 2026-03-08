"""Load dictionary files (JSON, CSV, line-based). One Document per entry: 'headword is definition.'"""
from pathlib import Path
import csv
import json
import re
from typing import Any

from ..schema import Document

# Extensions to scan when path is a directory
DICT_EXTENSIONS = (".json", ".csv", ".txt")


def _norm(s: str) -> str:
    """Strip and collapse whitespace."""
    return " ".join(str(s).strip().split()) if s else ""


def _make_text(headword: str, definition: str, pos: str | None = None) -> str:
    """One sentence: 'headword is definition.' Fits BE meaning pattern."""
    headword = _norm(headword)
    definition = _norm(definition)
    if not headword:
        return ""
    if not definition:
        definition = "(vocabulary term)"
    if pos and definition != "(vocabulary term)":
        return f"{headword} ({pos}) is {definition}."
    return f"{headword} is {definition}."


def _doc(headword: str, definition: str, pos: str | None, path: str) -> Document:
    text = _make_text(headword, definition, pos)
    meta: dict[str, Any] = {"headword": headword, "definition": definition, "path": path}
    if pos:
        meta["pos"] = pos
    return Document(text=text, source="dictionary", meta=meta)


def _parse_json(path: Path) -> list[Document]:
    docs: list[Document] = []
    pstr = str(path)
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return []

    # Object keyed by word: {"word": {"definition": "...", "all_defs": [...]}, ...}
    if isinstance(data, dict) and data and not isinstance(next(iter(data.values())), list):
        for headword, obj in data.items():
            if not isinstance(obj, dict):
                continue
            headword = _norm(headword)
            defn = obj.get("definition") or (obj.get("all_defs") or [None])[0]
            if defn is None:
                defn = ""
            if isinstance(defn, list):
                defn = defn[0] if defn else ""
            defn = _norm(str(defn)) if defn else ""
            pos = obj.get("pos") or obj.get("part_of_speech") or obj.get("type")
            pos = _norm(str(pos)) if pos else None
            if headword:
                docs.append(_doc(headword, defn, pos, pstr))
        return docs

    # Array of entries: [{"word": "...", "definition": "..."}, ...]
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            headword = (
                item.get("word") or item.get("headword") or item.get("keyword") or item.get("term") or ""
            )
            definition = (
                item.get("definition") or item.get("def") or item.get("meaning") or ""
            )
            pos = item.get("pos") or item.get("part_of_speech") or item.get("type")
            headword = _norm(str(headword))
            definition = _norm(str(definition))
            pos = _norm(str(pos)) if pos else None
            if headword:
                docs.append(_doc(headword, definition, pos, pstr))
        return docs

    # Object with "words" / "entries" key: {"words": [{...}, ...]}
    if isinstance(data, dict):
        arr = data.get("words") or data.get("entries") or data.get("definitions")
        if isinstance(arr, list):
            for item in arr:
                if not isinstance(item, dict):
                    continue
                headword = (
                    item.get("word") or item.get("headword") or item.get("keyword") or item.get("term") or ""
                )
                definition = (
                    item.get("definition") or item.get("def") or item.get("meaning") or ""
                )
                pos = item.get("pos") or item.get("part_of_speech") or item.get("type")
                headword = _norm(str(headword))
                definition = _norm(str(definition))
                pos = _norm(str(pos)) if pos else None
                if headword:
                    docs.append(_doc(headword, definition, pos, pstr))
            return docs
        # master_list: just words, no definitions
        master = data.get("master_list")
        if isinstance(master, list):
            for w in master:
                headword = _norm(str(w))
                if headword:
                    docs.append(_doc(headword, "", None, pstr))
            return docs

    return docs


def _parse_csv(path: Path) -> list[Document]:
    docs: list[Document] = []
    pstr = str(path)
    try:
        with open(path, encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
    except OSError:
        return []
    if not rows:
        return []
    # Heuristic: first row might be header (word, definition) or (word, pos, definition)
    for i, row in enumerate(rows):
        if not row:
            continue
        if i == 0 and row and _norm(row[0]).lower() in ("word", "headword", "term") and len(row) >= 2:
            continue
        if len(row) >= 2:
            headword = _norm(row[0])
            definition = _norm(row[1]) if len(row) > 1 else ""
            pos = _norm(row[2]) if len(row) > 2 else None
            if headword:
                docs.append(_doc(headword, definition, pos, pstr))
    return docs


def _parse_line_based(path: Path) -> list[Document]:
    docs: list[Document] = []
    pstr = str(path)
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # "word: definition" or "word\tdefinition"
        if "\t" in line:
            parts = line.split("\t", 1)
            headword, definition = _norm(parts[0]), _norm(parts[1]) if len(parts) > 1 else ""
        elif ":" in line:
            parts = line.split(":", 1)
            headword, definition = _norm(parts[0]), _norm(parts[1]) if len(parts) > 1 else ""
        else:
            continue
        if headword:
            docs.append(_doc(headword, definition, None, pstr))
    return docs


def load_dictionary(paths: list[str | Path]) -> list[Document]:
    """
    Load dictionary files (or directories). Supports JSON, CSV, and line-based (word: def or word\\tdef).
    Returns one Document per entry with text like 'headword is definition.' and source='dictionary'.
    """
    seen: set[str] = set()
    docs: list[Document] = []

    def add_file(fpath: Path) -> None:
        if not fpath.is_file():
            return
        key = str(fpath.resolve())
        if key in seen:
            return
        seen.add(key)
        suffix = fpath.suffix.lower()
        if suffix == ".json":
            docs.extend(_parse_json(fpath))
        elif suffix == ".csv":
            docs.extend(_parse_csv(fpath))
        elif suffix == ".txt":
            docs.extend(_parse_line_based(fpath))

    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        if path.is_file():
            add_file(path)
            continue
        for f in path.rglob("*"):
            if f.is_file() and f.suffix.lower() in DICT_EXTENSIONS:
                add_file(f)

    return docs
