"""Load browser bookmarks (Chrome, Firefox, Edge). Returns raw records for infer."""
from pathlib import Path
import json
from typing import Any


def load_bookmarks(paths: list[str | Path]) -> list[dict[str, Any]]:
    """
    Parse bookmark files; return list of {url, title, folder} for infer.
    Does not return Documents; use data.infer.bookmarks_to_docs() to convert.
    """
    records: list[dict[str, Any]] = []

    for p in paths:
        path = Path(p)
        if not path.exists() or not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
            data = json.loads(raw)
        except Exception:
            continue
        # Chrome / Edge: { "roots": { "bookmark_bar": { "children": [...] } } }
        if "roots" in data:
            for root_name, root in data.get("roots", {}).items():
                if isinstance(root, dict):
                    _collect_bookmarks(root, records, folder=root_name)
        # Firefox: { "children": [ { "children": [...] } ] }
        elif "children" in data:
            _collect_bookmarks(data, records, folder="")
        elif isinstance(data, list):
            for node in data:
                _collect_bookmarks(node, records, folder="")
    return records


def _collect_bookmarks(
    node: dict,
    records: list[dict[str, Any]],
    folder: str,
) -> None:
    if not isinstance(node, dict):
        return
    kind = node.get("type", "folder")
    title = node.get("title", "") or ""
    url = node.get("url", "")
    children = node.get("children", [])

    if kind == "url" and url:
        records.append({
            "url": url,
            "title": title,
            "folder": folder,
        })
    for child in children:
        child_folder = folder
        if isinstance(child, dict) and child.get("type") == "folder":
            child_folder = (folder + "/" + (child.get("title") or "")).strip("/")
        _collect_bookmarks(child, records, child_folder)
