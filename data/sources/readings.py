"""Load reading-list exports (Pocket, Instapaper, etc.). Returns raw records for infer."""
from pathlib import Path
import json
import re
from typing import Any

from ..schema import Document


def load_readings(paths: list[str | Path]) -> list[dict[str, Any]] | list[Document]:
    """
    Parse reading export (HTML or JSON). Returns list of {url, title, snippet} dicts
    for infer, or Document list if already plain text. Use data.infer.readings_to_docs() to convert.
    """
    records: list[dict[str, Any]] = []

    for p in paths:
        path = Path(p)
        if not path.exists() or not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".json":
            _parse_json_readings(path, records)
        elif suffix in (".html", ".htm"):
            _parse_html_readings(path, records)
    return records


def _parse_json_readings(path: Path, records: list[dict[str, Any]]) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                records.append({
                    "url": item.get("url", item.get("given_url", "")),
                    "title": item.get("title", item.get("resolved_title", "")),
                    "snippet": item.get("excerpt", item.get("summary", "")),
                })
    elif isinstance(data, dict) and "list" in data:
        for item in data.get("list", []):
            if isinstance(item, dict):
                records.append({
                    "url": item.get("url", item.get("given_url", "")),
                    "title": item.get("title", item.get("resolved_title", "")),
                    "snippet": item.get("excerpt", item.get("summary", "")),
                })


def _parse_html_readings(path: Path, records: list[dict[str, Any]]) -> None:
    try:
        html = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return
    # Pocket export: <a href="..." add_date="...">Title</a>
    for m in re.finditer(
        r'<a\s+href="([^"]+)"[^>]*>([^<]*)</a>',
        html,
        re.IGNORECASE,
    ):
        url, title = m.group(1).strip(), m.group(2).strip()
        if url and (url.startswith("http") or url.startswith("file")):
            records.append({"url": url, "title": title, "snippet": ""})
