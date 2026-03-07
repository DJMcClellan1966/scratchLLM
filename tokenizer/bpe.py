"""BPE tokenizer: train on corpus, encode/decode, save/load. Vocab size from scaling."""
from __future__ import annotations
import json
import re
from pathlib import Path
from collections import Counter
from typing import Optional


class BPETokenizer:
    """Byte-pair encoding tokenizer. Train on text, then encode/decode."""

    def __init__(
        self,
        vocab: Optional[dict[str, int]] = None,
        merges: Optional[list[tuple[str, str]]] = None,
        special_tokens: Optional[list[str]] = None,
    ) -> None:
        self.special_tokens = special_tokens or ["<|pad|>", "<|eos|>", "<|unk|>"]
        self.vocab: dict[str, int] = dict(vocab) if vocab else {}
        self.merges: list[tuple[str, str]] = list(merges) if merges else []
        self.reverse_vocab: dict[int, str] = {v: k for k, v in self.vocab.items()}

    @property
    def vocab_size(self) -> int:
        return len(self.vocab)

    def train(
        self,
        texts: list[str],
        vocab_size: int = 8192,
        min_frequency: int = 2,
    ) -> None:
        """Train BPE on list of text strings. Builds vocab and merges."""
        # Start with bytes + special tokens
        self.vocab = {}
        idx = 0
        for t in self.special_tokens:
            self.vocab[t] = idx
            idx += 1
        for i in range(256):
            self.vocab[chr(i)] = idx
            idx += 1

        # Tokenize to bytes (per word-ish) for training
        def tokenize_for_bpe(text: str) -> list[str]:
            words = re.findall(r"'?[a-zA-Z]+'?|[0-9]+|[^\s\w]+|\s+", text)
            out = []
            for w in words:
                out.extend(list(w.encode("utf-8").decode("latin-1")))
            return out

        corpus_tokens: list[list[str]] = []
        for text in texts:
            if not text.strip():
                continue
            corpus_tokens.append(tokenize_for_bpe(text))

        # Count pairs
        def get_pairs(tokens: list[str]) -> Counter:
            c: Counter = Counter()
            for i in range(len(tokens) - 1):
                c[(tokens[i], tokens[i + 1])] += 1
            return c

        def merge(tokens: list[str], pair: tuple[str, str], new_tok: str) -> list[str]:
            out = []
            i = 0
            while i < len(tokens):
                if i < len(tokens) - 1 and (tokens[i], tokens[i + 1]) == pair:
                    out.append(new_tok)
                    i += 2
                else:
                    out.append(tokens[i])
                    i += 1
            return out

        self.merges = []
        while len(self.vocab) + len(self.merges) < vocab_size:
            pair_counts: Counter = Counter()
            for tokens in corpus_tokens:
                pair_counts.update(get_pairs(tokens))
            if not pair_counts:
                break
            (pair, _) = pair_counts.most_common(1)[0]
            if pair_counts[pair] < min_frequency:
                break
            new_tok = pair[0] + pair[1]
            if new_tok not in self.vocab:
                self.vocab[new_tok] = len(self.vocab)
            self.merges.append(pair)
            corpus_tokens = [merge(tokens, pair, new_tok) for tokens in corpus_tokens]

        self.reverse_vocab = {v: k for k, v in self.vocab.items()}

    def encode(self, text: str) -> list[int]:
        """Encode text to token ids (byte-level BPE: bytes then merge rules)."""
        if not self.vocab:
            return []
        # Start with bytes as single-char tokens (latin-1 preserves byte values)
        tokens: list[str] = list(text.encode("utf-8").decode("latin-1"))
        for (a, b) in self.merges:
            new_tok = a + b
            if new_tok not in self.vocab:
                continue
            i = 0
            while i < len(tokens) - 1:
                if (tokens[i], tokens[i + 1]) == (a, b):
                    tokens = tokens[:i] + [new_tok] + tokens[i + 2:]
                else:
                    i += 1
        unk_id = self.vocab.get("<|unk|>", 0)
        return [self.vocab.get(t, unk_id) for t in tokens]

    def decode(self, ids: list[int]) -> str:
        """Decode token ids to text."""
        if not self.reverse_vocab:
            return ""
        try:
            chars = []
            for i in ids:
                try:
                    tid = int(i)
                except (TypeError, ValueError):
                    continue
                t = self.reverse_vocab.get(tid, "<|unk|>")
                if t in self.special_tokens:
                    if t == "<|eos|>":
                        break
                    continue
                chars.append(t)
            raw = "".join(chars)
            return raw.encode("latin-1").decode("utf-8", errors="replace")
        except Exception:
            try:
                return "".join(chars) if chars else ""
            except Exception:
                return ""


def save_tokenizer(tokenizer: BPETokenizer, path: str | Path) -> None:
    """Save tokenizer to directory: vocab.json and merges.json."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    with open(path / "vocab.json", "w", encoding="utf-8") as f:
        json.dump(tokenizer.vocab, f, ensure_ascii=False)
    with open(path / "merges.json", "w", encoding="utf-8") as f:
        json.dump([[a, b] for a, b in tokenizer.merges], f)
    with open(path / "special_tokens.json", "w", encoding="utf-8") as f:
        json.dump(tokenizer.special_tokens, f)


def load_tokenizer(path: str | Path) -> BPETokenizer:
    """Load tokenizer from directory."""
    path = Path(path)
    with open(path / "vocab.json", encoding="utf-8") as f:
        vocab = json.load(f)
    with open(path / "merges.json", encoding="utf-8") as f:
        merges = [tuple(x) for x in json.load(f)]
    special_path = path / "special_tokens.json"
    special_tokens = ["<|pad|>", "<|eos|>", "<|unk|>"]
    if special_path.exists():
        with open(special_path, encoding="utf-8") as f:
            special_tokens = json.load(f)
    return BPETokenizer(vocab=vocab, merges=merges, special_tokens=special_tokens)
