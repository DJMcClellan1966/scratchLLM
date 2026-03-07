"""Turn bookmark/reading records into inferred text documents (no LLM calls)."""
from .schema import Document


def bookmarks_to_docs(records: list[dict]) -> list[Document]:
    """Convert list of {url, title, folder} to Document list with inferred text."""
    docs: list[Document] = []
    for r in records:
        url = r.get("url", "")
        title = r.get("title", "") or ""
        folder = r.get("folder", "") or ""
        parts = []
        if title:
            parts.append(f"Title: {title}")
        if url:
            parts.append(f"URL: {url}")
        if folder:
            parts.append(f"Topic: {folder}")
        text = "\n".join(parts).strip()
        if text:
            docs.append(
                Document(
                    text=text,
                    source="inferred_bookmarks",
                    meta={"url": url, "title": title, "folder": folder},
                )
            )
    return docs


def readings_to_docs(records: list[dict]) -> list[Document]:
    """Convert list of {url, title, snippet} to Document list with inferred text."""
    docs: list[Document] = []
    for r in records:
        url = r.get("url", "")
        title = r.get("title", "") or ""
        snippet = r.get("snippet", "") or ""
        parts = []
        if title:
            parts.append(f"Title: {title}")
        if url:
            parts.append(f"URL: {url}")
        if snippet:
            parts.append(snippet[:500] if len(snippet) > 500 else snippet)
        text = "\n".join(parts).strip()
        if text:
            docs.append(
                Document(
                    text=text,
                    source="inferred_readings",
                    meta={"url": url, "title": title},
                )
            )
    return docs
