"""Optional: fetch URL content for corpus enrichment. Rate-limited, local use only."""
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from .schema import Document

# Optional deps for fetching
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_FETCH_DEPS = True
except ImportError:
    HAS_FETCH_DEPS = False

DEFAULT_DELAY = 1.0  # seconds between requests
DEFAULT_TIMEOUT = 10
MAX_BODY_CHARS = 50_000


def fetch_url(
    url: str,
    timeout: float = DEFAULT_TIMEOUT,
    max_chars: int = MAX_BODY_CHARS,
) -> Optional[str]:
    """Fetch URL and return main text (no LLM). Returns None on failure."""
    if not HAS_FETCH_DEPS:
        return None
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        html = resp.text
    except Exception:
        return None
    return extract_main_text(html, max_chars=max_chars)


def extract_main_text(html: str, max_chars: int = MAX_BODY_CHARS) -> str:
    """Extract main text from HTML using BeautifulSoup."""
    if not HAS_FETCH_DEPS:
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in ("script", "style", "nav", "footer", "header"):
            for e in soup.find_all(tag):
                e.decompose()
        body = soup.find("body") or soup
        text = body.get_text(separator="\n", strip=True)
        return text[:max_chars] if text else ""
    except Exception:
        return ""


def fetch_urls_to_docs(
    url_title_list: list[tuple[str, str]],
    delay: float = DEFAULT_DELAY,
    timeout: float = DEFAULT_TIMEOUT,
    max_chars: int = MAX_BODY_CHARS,
) -> list[Document]:
    """
    Given list of (url, title), fetch each URL and return Document with title + extracted text.
    Rate-limited by delay. Used only for corpus enrichment (LOCAL_STACK).
    """
    docs: list[Document] = []
    for url, title in url_title_list:
        if delay > 0:
            time.sleep(delay)
        body = fetch_url(url, timeout=timeout, max_chars=max_chars)
        if not body and not title:
            continue
        text = f"Title: {title}\n\n{body}".strip() if title else (body or "")
        if text:
            docs.append(
                Document(
                    text=text,
                    source="fetched",
                    meta={"url": url, "title": title},
                )
            )
    return docs


def allowlist_domain(url: str, allowlist: Optional[list[str]]) -> bool:
    """Return True if allowlist is None or url's domain is in allowlist."""
    if not allowlist:
        return True
    try:
        domain = urlparse(url).netloc.lower()
        return any(d.lower() in domain or domain.endswith("." + d.lower()) for d in allowlist)
    except Exception:
        return False
