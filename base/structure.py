"""Structural representation: format context with [FACT], [CONTEXT], [PROMPT] roles."""
from dataclasses import dataclass
from typing import Optional

# SegmentInfo: (start_idx, end_idx, role) in token space, or (start_char, end_char, role)
SegmentInfo = tuple[int, int, str]


@dataclass
class FormattedContext:
    """Context string plus optional segment boundaries (character or token indices)."""

    context_string: str
    segment_info: list[SegmentInfo]  # (start, end, role); role in ("FACT", "CONTEXT", "PROMPT")


def format_context(
    truth_chunks: list[str],
    corpus_chunks: list[str],
    prompt: str,
    tokenizer: Optional[object] = None,
    context_len: Optional[int] = None,
) -> FormattedContext:
    """
    Build a single context string with [FACT], [CONTEXT], [PROMPT] segments.
    Optionally truncate to context_len (keeping prompt at end) and return segment_info in token space.
    """
    fact_block = "\n".join(truth_chunks).strip() if truth_chunks else ""
    context_block = "\n".join(corpus_chunks).strip() if corpus_chunks else ""
    parts = []
    if fact_block:
        parts.append("[FACT]\n" + fact_block)
    if context_block:
        parts.append("[CONTEXT]\n" + context_block)
    parts.append("[PROMPT]\n" + prompt.strip())
    context_string = "\n\n".join(parts)

    # Segment info in character space (for the full string)
    segment_info_char: list[SegmentInfo] = []
    pos = 0
    if fact_block:
        start = context_string.find("[FACT]\n") + len("[FACT]\n")
        end = context_string.find("\n\n[CONTEXT]", start) if context_block else context_string.find("\n\n[PROMPT]", start)
        if end == -1:
            end = len(context_string)
        segment_info_char.append((start, end, "FACT"))
        pos = end
    if context_block:
        start = context_string.find("[CONTEXT]\n") + len("[CONTEXT]\n")
        end = context_string.find("\n\n[PROMPT]", start)
        if end == -1:
            end = len(context_string)
        segment_info_char.append((start, end, "CONTEXT"))
        pos = end
    start = context_string.find("[PROMPT]\n") + len("[PROMPT]\n")
    segment_info_char.append((start, len(context_string), "PROMPT"))

    if tokenizer is not None and context_len is not None and hasattr(tokenizer, "encode"):
        ids = tokenizer.encode(context_string)
        if len(ids) > context_len:
            ids = ids[-context_len:]
            context_string = tokenizer.decode(ids) if hasattr(tokenizer, "decode") else context_string
        # Recompute segment info from truncated string (markers may have been cut)
        segment_info_tokens = _segments_in_decoded_to_tokens(tokenizer, context_string, ids)
        return FormattedContext(context_string=context_string, segment_info=segment_info_tokens)

    return FormattedContext(context_string=context_string, segment_info=segment_info_char)


def _segments_in_decoded_to_tokens(
    tokenizer: object,
    decoded: str,
    ids: list[int],
) -> list[SegmentInfo]:
    """Find [FACT], [CONTEXT], [PROMPT] in decoded string and return (start_tok, end_tok, role)."""
    if not hasattr(tokenizer, "decode") or not ids:
        return []
    result: list[SegmentInfo] = []
    markers = [("[FACT]\n", "FACT"), ("[CONTEXT]\n", "CONTEXT"), ("[PROMPT]\n", "PROMPT")]
    pos = 0
    for marker, role in markers:
        i = decoded.find(marker, pos)
        if i == -1:
            continue
        start_char = i + len(marker)
        # End = start of next marker or end of string
        end_char = len(decoded)
        for m, _ in markers:
            j = decoded.find(m, start_char)
            if j != -1 and j < end_char:
                end_char = j
        tok_start, tok_end = _char_range_to_tokens(tokenizer, ids, start_char, end_char)
        if tok_end > tok_start:
            result.append((tok_start, tok_end, role))
        pos = end_char
    return result


def _char_range_to_tokens(
    tokenizer: object,
    ids: list[int],
    start_char: int,
    end_char: int,
) -> tuple[int, int]:
    """Map character range to token indices using tokenizer.decode per token."""
    if not ids or not hasattr(tokenizer, "decode"):
        return (0, len(ids))
    pos = 0
    tok_start, tok_end = 0, len(ids)
    for i, tid in enumerate(ids):
        chunk = tokenizer.decode([tid])
        next_pos = pos + len(chunk)
        if pos <= start_char < next_pos:
            tok_start = i
        if pos < end_char <= next_pos:
            tok_end = i + 1
            break
        pos = next_pos
    return (tok_start, min(tok_end, len(ids)))
