"""
Gödel-style encoding of LLM encodings (token sequences, meaning structs, statements) into
natural numbers. Inspired by Gödel numbering: symbols and formulas are mapped to numbers
so the system can "speak about itself" (meta-reasoning, limit analysis).

We encode:
- Token ID sequences -> prime-power encoding (2^(n0+1) * 3^(n1+1) * ...).
- MeaningStruct (canonical JSON) -> byte sequence -> same prime-power encoding.
- Statement (to_dict, canonical JSON) -> byte sequence -> same encoding.

Note: Prime encoding grows exponentially with sequence length; keep sequences short in practice.
We do not implement a formal system or incompleteness proof—only the encoding/decoding.
"""
import json
from typing import Any

# MeaningStruct from language (avoid circular import at module load)
MeaningStruct = dict[str, Any]


def _primes() -> "list[int]":
    """First primes; extend as needed for decode. Lazy list for encoding."""
    return [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]


def _n_primes(n: int) -> list[int]:
    """First n primes (trial division)."""
    if n <= 0:
        return []
    out: list[int] = [2]
    k = 3
    while len(out) < n:
        is_prime = True
        for p in out:
            if p * p > k:
                break
            if k % p == 0:
                is_prime = False
                break
        if is_prime:
            out.append(k)
        k += 2
    return out


def _encode_sequence(values: list[int], max_val: int = 0) -> int:
    """Encode list of non-negative integers as 2^(v0+1) * 3^(v1+1) * ... . Empty -> 1."""
    if not values:
        return 1
    primes = _n_primes(len(values))
    result = 1
    for p, v in zip(primes, values):
        if v < 0:
            raise ValueError("Gödel encoding requires non-negative values")
        result *= p ** (v + 1)  # +1 so 0 is representable
    return result


def _decode_sequence(n: int) -> list[int]:
    """Decode number into sequence of non-negative integers (exponents minus 1)."""
    if n <= 0:
        raise ValueError("Gödel decode requires positive integer")
    if n == 1:
        return []
    out: list[int] = []
    num_primes = 64
    idx = 0
    while n > 1:
        primes = _n_primes(num_primes)
        if idx >= len(primes):
            num_primes += 64
            continue
        p = primes[idx]
        exp = 0
        while n % p == 0:
            n //= p
            exp += 1
        if exp > 0:
            out.append(exp - 1)
        idx += 1
    return out


def encode_token_sequence(ids: list[int]) -> int:
    """Encode a token ID sequence as a single natural number (Gödel number). Empty list -> 1."""
    for i in ids:
        if i < 0:
            raise ValueError("Token IDs must be non-negative")
    return _encode_sequence(ids)


def decode_token_sequence(n: int) -> list[int]:
    """Decode a Gödel number back to the token ID sequence. n must be positive; 1 -> []."""
    if n <= 0:
        raise ValueError("Gödel decode requires positive integer")
    return _decode_sequence(n)


def _canonical_json(obj: dict[str, Any]) -> bytes:
    """Serialize dict to canonical JSON (sorted keys, no extra whitespace) as UTF-8 bytes."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def encode_meaning(m: MeaningStruct) -> int:
    """Encode a meaning struct (BE/QUERY/PRED) as a natural number. Uses canonical JSON -> bytes -> prime encoding."""
    if not isinstance(m, dict):
        raise TypeError("MeaningStruct must be a dict")
    # Only string values in our schema; normalize to dict with string values for canonical form
    clean: dict[str, Any] = {k: (v if isinstance(v, str) else str(v)) for k, v in m.items()}
    b = _canonical_json(clean)
    return _encode_sequence(list(b))


def decode_meaning(n: int) -> MeaningStruct:
    """Decode a Gödel number to a meaning struct. Raises if n is invalid or JSON is not a dict."""
    if n <= 0:
        raise ValueError("Gödel decode requires positive integer")
    if n == 1:
        return {}  # empty struct
    seq = _decode_sequence(n)
    if any(v < 0 or v > 255 for v in seq):
        raise ValueError("Decoded sequence contains invalid byte value")
    b = bytes(seq)
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError("Decoded bytes are not valid UTF-8") from e
    try:
        obj = json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError("Decoded string is not valid JSON") from e
    if not isinstance(obj, dict):
        raise ValueError("Decoded JSON is not a dict")
    return obj


def encode_statement(s: "Any") -> int:
    """Encode a Statement as a natural number (via to_dict -> canonical JSON -> bytes -> prime encoding)."""
    from .truth_base import Statement
    if not isinstance(s, Statement):
        raise TypeError("encode_statement requires a Statement")
    d = s.to_dict()
    b = _canonical_json(d)
    return _encode_sequence(list(b))


def decode_statement(n: int) -> "Statement":
    """Decode a Gödel number to a Statement. Raises if n is invalid or JSON does not match Statement schema."""
    from .truth_base import Statement
    if n <= 0:
        raise ValueError("Gödel decode requires positive integer")
    if n == 1:
        return Statement(text="", tier=0, source="curated")
    seq = _decode_sequence(n)
    if any(v < 0 or v > 255 for v in seq):
        raise ValueError("Decoded sequence contains invalid byte value")
    b = bytes(seq)
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError("Decoded bytes are not valid UTF-8") from e
    try:
        obj = json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError("Decoded string is not valid JSON") from e
    if not isinstance(obj, dict):
        raise ValueError("Decoded JSON is not a dict")
    return Statement.from_dict(obj)
