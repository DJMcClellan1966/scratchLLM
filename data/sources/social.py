"""Load social media exports (e.g. Twitter/Reddit JSON)."""
from pathlib import Path
import json
from ..schema import Document


def load_social(paths: list[str | Path]) -> list[Document]:
    """Parse provider export JSON; yield one doc per post/comment."""
    docs: list[Document] = []

    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        if path.is_file():
            _parse_file(path, docs)
        else:
            for f in path.rglob("*.json"):
                _parse_file(f, docs)
    return docs


def _parse_file(path: Path, docs: list[Document]) -> None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        data = json.loads(raw)
    except Exception:
        return
    if isinstance(data, list):
        for item in data:
            _extract_item(item, docs, str(path))
    elif isinstance(data, dict):
        # Twitter: { "tweets": [...] } or direct list in key
        if "tweets" in data:
            for item in data["tweets"]:
                _extract_item(item, docs, str(path))
        elif "statuses" in data:
            for item in data["statuses"]:
                _extract_item(item, docs, str(path))
        elif "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                _extract_item(item, docs, str(path))
        else:
            _extract_item(data, docs, str(path))
    return


def _extract_item(item: dict, docs: list[Document], path: str) -> None:
    if not isinstance(item, dict):
        return
    text = (
        item.get("full_text")
        or item.get("text")
        or item.get("body")
        or item.get("content")
        or item.get("title", "")
    )
    if isinstance(text, str) and text.strip():
        docs.append(
            Document(
                text=text.strip(),
                source="social",
                meta={"path": path, "id": item.get("id")},
            )
        )
    title = item.get("title")
    if title and isinstance(title, str) and title.strip() and title != text:
        docs.append(
            Document(
                text=title.strip(),
                source="social",
                meta={"path": path, "type": "title"},
            )
        )
