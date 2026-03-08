"""Load text files (.txt, .md) from bible-commentary paths. One doc per file, source='bible_commentary'."""
from pathlib import Path

from ..schema import Document

# Extensions to load (commentary, studies, docs)
BIBLE_COMMENTARY_EXTENSIONS = (".txt", ".md")


def load_bible_commentary(
    paths: list[str | Path],
    extensions: tuple[str, ...] = BIBLE_COMMENTARY_EXTENSIONS,
) -> list[Document]:
    """Scan dirs for .txt and .md files; yield one doc per file with source='bible_commentary'."""
    docs: list[Document] = []
    seen: set[str] = set()

    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        if path.is_file():
            if path.suffix.lower() in extensions:
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                    docs.append(
                        Document(
                            text=text,
                            source="bible_commentary",
                            meta={"path": str(path)},
                        )
                    )
                except OSError:
                    pass
            continue
        for f in path.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in extensions:
                continue
            try:
                key = str(f.resolve())
                if key in seen:
                    continue
                seen.add(key)
                text = f.read_text(encoding="utf-8", errors="replace")
                docs.append(
                    Document(
                        text=text,
                        source="bible_commentary",
                        meta={"path": str(f)},
                    )
                )
            except OSError:
                pass
    return docs
