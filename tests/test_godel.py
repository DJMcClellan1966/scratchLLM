"""Tests for Gödel encoding/decoding of token sequences, meaning structs, and statements."""
import pytest

from base.godel import (
    encode_token_sequence,
    decode_token_sequence,
    encode_meaning,
    decode_meaning,
    encode_statement,
    decode_statement,
)


def test_encode_empty_token_sequence():
    assert encode_token_sequence([]) == 1


def test_decode_one_returns_empty():
    assert decode_token_sequence(1) == []


def test_token_sequence_roundtrip_empty():
    assert decode_token_sequence(encode_token_sequence([])) == []


def test_token_sequence_roundtrip_single():
    x = [0]
    assert decode_token_sequence(encode_token_sequence(x)) == x


def test_token_sequence_roundtrip_two():
    x = [1, 0]
    assert decode_token_sequence(encode_token_sequence(x)) == x


def test_token_sequence_roundtrip_three():
    x = [0, 1, 2]
    assert decode_token_sequence(encode_token_sequence(x)) == x


def test_token_sequence_decode_invalid_raises():
    with pytest.raises(ValueError):
        decode_token_sequence(0)
    with pytest.raises(ValueError):
        decode_token_sequence(-1)


def test_encode_meaning_be():
    m = {"type": "BE", "subj": "2 + 2", "obj": "4"}
    n = encode_meaning(m)
    assert isinstance(n, int)
    assert n >= 1
    back = decode_meaning(n)
    assert back["type"] == m["type"]
    assert back["subj"] == m["subj"]
    assert back["obj"] == m["obj"]


def test_encode_meaning_query():
    m = {"type": "QUERY", "ref": "capital of France"}
    back = decode_meaning(encode_meaning(m))
    assert back["type"] == m["type"]
    assert back["ref"] == m["ref"]


def test_encode_meaning_pred():
    m = {"type": "PRED", "subj": "Earth", "pred": "revolves around", "obj": "Sun"}
    back = decode_meaning(encode_meaning(m))
    assert back["type"] == m["type"]
    assert back["subj"] == m["subj"]
    assert back["pred"] == m["pred"]
    assert back["obj"] == m["obj"]


def test_meaning_roundtrip_canonical_order():
    m = {"type": "BE", "obj": "4", "subj": "2+2"}
    back = decode_meaning(encode_meaning(m))
    assert set(back.keys()) == set(m.keys())
    assert back["type"] == m["type"]
    assert back["subj"] == m["subj"]
    assert back["obj"] == m["obj"]


def test_decode_meaning_empty_strings():
    m = {"type": "BE", "subj": "", "obj": ""}
    back = decode_meaning(encode_meaning(m))
    assert back["subj"] == ""
    assert back["obj"] == ""


def test_decode_meaning_invalid_raises():
    with pytest.raises(ValueError):
        decode_meaning(0)
    with pytest.raises(ValueError):
        decode_meaning(-1)


def test_encode_statement_roundtrip_without_meaning():
    from base.truth_base import Statement
    s = Statement(text="2+2=4", tier=0, source="curated")
    back = decode_statement(encode_statement(s))
    assert back.text == s.text
    assert back.tier == s.tier
    assert back.source == s.source
    assert back.meaning is None


def test_encode_statement_roundtrip_with_meaning():
    from base.truth_base import Statement
    meaning = {"type": "BE", "subj": "2+2", "obj": "4"}
    s = Statement(text="2+2=4", tier=0, source="curated", meaning=meaning)
    back = decode_statement(encode_statement(s))
    assert back.text == s.text
    assert back.tier == s.tier
    assert back.meaning is not None
    assert back.meaning["type"] == meaning["type"]
    assert back.meaning["subj"] == meaning["subj"]
    assert back.meaning["obj"] == meaning["obj"]


def test_decode_statement_one():
    from base.truth_base import Statement
    s = decode_statement(1)
    assert s.text == ""
    assert s.tier == 0
    assert s.source == "curated"


def test_decode_statement_invalid_raises():
    with pytest.raises(ValueError):
        decode_statement(0)
    with pytest.raises(ValueError):
        decode_statement(-1)


def test_encode_token_sequence_negative_raises():
    with pytest.raises(ValueError):
        encode_token_sequence([-1])
    with pytest.raises(ValueError):
        encode_token_sequence([0, -1, 2])
