"""Load email from mbox or similar export formats."""
from pathlib import Path
import email
from ..schema import Document


def load_email(paths: list[str | Path]) -> list[Document]:
    """Read mbox or .eml files; yield one doc per message (subject + body)."""
    docs: list[Document] = []

    for p in paths:
        path = Path(p)
        if not path.exists() or not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".eml":
            try:
                raw = path.read_bytes()
                msg = email.message_from_bytes(raw)
                subj = msg.get("Subject", "") or ""
                body = _get_body(msg)
                text = f"Subject: {subj}\n\n{body}".strip()
                if text:
                    docs.append(
                        Document(
                            text=text,
                            source="email",
                            meta={"path": str(path)},
                        )
                    )
            except Exception:
                pass
            continue
        if suffix in (".mbox", ".mbx", "") or "mail" in path.name.lower():
            try:
                for msg in _iter_mbox(path):
                    subj = msg.get("Subject", "") or ""
                    body = _get_body(msg)
                    text = f"Subject: {subj}\n\n{body}".strip()
                    if text:
                        docs.append(Document(text=text, source="email", meta={}))
            except Exception:
                pass
    return docs


def _get_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    return part.get_payload(decode=True).decode("utf-8", errors="replace")
                except Exception:
                    pass
        for part in msg.walk():
            if part.get_content_type().startswith("text/"):
                try:
                    return part.get_payload(decode=True).decode("utf-8", errors="replace")
                except Exception:
                    pass
        return ""
    try:
        payload = msg.get_payload(decode=True)
        return payload.decode("utf-8", errors="replace") if payload else ""
    except Exception:
        return ""


def _iter_mbox(path: Path):
    """Yield email.message.Message from mbox-style file."""
    import mailbox
    try:
        mb = mailbox.mbox(str(path))
        for key in mb.keys():
            try:
                yield mb.get_message(key)
            except Exception:
                pass
        return
    except Exception:
        pass
    # Fallback: try reading as single messages delimited by From_
    try:
        content = path.read_bytes()
        content = content.decode("utf-8", errors="replace")
        parts = content.split("\nFrom ")
        for i, part in enumerate(parts):
            if not part.strip():
                continue
            if i > 0:
                part = "From " + part
            try:
                yield email.message_from_string(part)
            except Exception:
                pass
    except Exception:
        pass
