"""Load text files (.txt, .md) from directories."""
from pathlib import Path
from ..schema import Document


def load_text_files(
    paths: list[str | Path],
    extensions: tuple[str, ...] = (".txt", ".md"),
) -> list[Document]:
    """Scan dirs for text files; yield one doc per file. paths can be files or dirs."""
    docs: list[Document] = []
    seen = set()

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
                            source="text_files",
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
                    Document(text=text, source="text_files", meta={"path": str(f)})
                )
            except OSError:
                pass
    return docs
