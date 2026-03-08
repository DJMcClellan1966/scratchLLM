"""Aggregate all sources into one corpus; compute stats; write manifest and corpus.jsonl."""
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from .schema import Document

try:
    from base.tiers import tier_from_source
except ImportError:
    def tier_from_source(source: str) -> int:
        return 3  # inference
from .infer import bookmarks_to_docs, readings_to_docs
from .fetch import fetch_urls_to_docs, allowlist_domain
from .sources.text_files import load_text_files
from .sources.email import load_email
from .sources.social import load_social
from .sources.bookmarks import load_bookmarks
from .sources.readings import load_readings
from .sources.dictionary import load_dictionary
from .sources.bible_commentary import load_bible_commentary


@dataclass
class CorpusManifest:
    """Manifest written next to corpus; used by training and scaling."""

    n_docs: int
    n_chars: int
    n_tokens_actual: int  # from tokenizer or estimate chars//4
    n_tokens_inferred: int  # inferred docs contribution
    paths_used: dict[str, list[str]] = field(default_factory=dict)
    scaling_inputs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CorpusManifest":
        return cls(
            n_docs=d.get("n_docs", 0),
            n_chars=d.get("n_chars", 0),
            n_tokens_actual=d.get("n_tokens_actual", 0),
            n_tokens_inferred=d.get("n_tokens_inferred", 0),
            paths_used=d.get("paths_used", {}),
            scaling_inputs=d.get("scaling_inputs", {}),
        )


def build_corpus(
    text_paths: Optional[list[str | Path]] = None,
    email_paths: Optional[list[str | Path]] = None,
    social_paths: Optional[list[str | Path]] = None,
    bookmark_paths: Optional[list[str | Path]] = None,
    reading_paths: Optional[list[str | Path]] = None,
    dictionary_paths: Optional[list[str | Path]] = None,
    bible_commentary_paths: Optional[list[str | Path]] = None,
    fetch_bookmark_urls: bool = False,
    fetch_delay: float = 1.0,
    fetch_allowlist: Optional[list[str]] = None,
    out_dir: Optional[str | Path] = None,
    estimate_tokens: bool = True,
    tier_map: Optional[dict[str, int]] = None,
) -> tuple[list[Document], CorpusManifest]:
    """
    Run all source loaders, infer from bookmarks/readings, optionally fetch URLs.
    Returns (list of documents, manifest). If out_dir is set, writes corpus.jsonl and manifest.json.
    """
    text_paths = text_paths or []
    email_paths = email_paths or []
    social_paths = social_paths or []
    bookmark_paths = bookmark_paths or []
    reading_paths = reading_paths or []
    dictionary_paths = dictionary_paths or []
    bible_commentary_paths = bible_commentary_paths or []

    docs: list[Document] = []
    paths_used: dict[str, list[str]] = {}

    if text_paths:
        d = load_text_files(text_paths)
        docs.extend(d)
        paths_used["text"] = [str(Path(p).resolve()) for p in text_paths]
    if email_paths:
        d = load_email(email_paths)
        docs.extend(d)
        paths_used["email"] = [str(Path(p).resolve()) for p in email_paths]
    if social_paths:
        d = load_social(social_paths)
        docs.extend(d)
        paths_used["social"] = [str(Path(p).resolve()) for p in social_paths]

    bookmark_records: list[dict] = []
    if bookmark_paths:
        bookmark_records = load_bookmarks(bookmark_paths)
        paths_used["bookmarks"] = [str(Path(p).resolve()) for p in bookmark_paths]
    inferred_bookmark_docs = bookmarks_to_docs(bookmark_records)
    docs.extend(inferred_bookmark_docs)

    reading_records: list[dict] = []
    if reading_paths:
        reading_records = load_readings(reading_paths)
        paths_used["readings"] = [str(Path(p).resolve()) for p in reading_paths]
    inferred_reading_docs = readings_to_docs(reading_records)
    docs.extend(inferred_reading_docs)

    if dictionary_paths:
        dict_docs = load_dictionary(dictionary_paths)
        docs.extend(dict_docs)
        paths_used["dictionary"] = [str(Path(p).resolve()) for p in dictionary_paths]

    if bible_commentary_paths:
        bc_docs = load_bible_commentary(bible_commentary_paths)
        docs.extend(bc_docs)
        paths_used["bible_commentary"] = [str(Path(p).resolve()) for p in bible_commentary_paths]

    if fetch_bookmark_urls and bookmark_records:
        url_title = [
            (r["url"], r.get("title", ""))
            for r in bookmark_records
            if r.get("url") and allowlist_domain(r["url"], fetch_allowlist)
        ]
        fetched = fetch_urls_to_docs(url_title, delay=fetch_delay)
        docs.extend(fetched)

    # Assign tier to each doc (for retrieval by tier). Persisted in meta.
    for i, doc in enumerate(docs):
        tier = (tier_map.get(doc.source, tier_from_source(doc.source)) if tier_map
                else tier_from_source(doc.source))
        meta = dict(doc.meta or {})
        meta["tier"] = tier
        docs[i] = Document(text=doc.text, source=doc.source, meta=meta)

    n_docs = len(docs)
    n_chars = sum(len(d.text) for d in docs)
    n_tokens_actual = n_chars // 4 if estimate_tokens else 0
    n_inferred = len(inferred_bookmark_docs) + len(inferred_reading_docs)
    n_tokens_inferred = sum(len(d.text) for d in inferred_bookmark_docs + inferred_reading_docs) // 4

    manifest = CorpusManifest(
        n_docs=n_docs,
        n_chars=n_chars,
        n_tokens_actual=n_tokens_actual,
        n_tokens_inferred=n_tokens_inferred,
        paths_used=paths_used,
        scaling_inputs={
            "n_tokens_actual": n_tokens_actual,
            "n_tokens_inferred": n_tokens_inferred,
            "n_docs": n_docs,
        },
    )

    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        corpus_path = out_dir / "corpus.jsonl"
        with open(corpus_path, "w", encoding="utf-8") as f:
            for d in docs:
                f.write(json.dumps(d.to_dict(), ensure_ascii=False) + "\n")
        manifest_path = out_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)

    return docs, manifest


def load_manifest(manifest_path: str | Path) -> CorpusManifest:
    """Load manifest from JSON file."""
    with open(manifest_path, encoding="utf-8") as f:
        return CorpusManifest.from_dict(json.load(f))


def load_corpus_jsonl(corpus_path: str | Path) -> list[Document]:
    """Load documents from corpus.jsonl."""
    docs: list[Document] = []
    with open(corpus_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            docs.append(Document.from_dict(json.loads(line)))
    return docs
