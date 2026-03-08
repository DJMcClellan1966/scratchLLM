"""Dataset: read corpus, tokenize, yield fixed-length chunks for training."""
import random
from pathlib import Path
from typing import Optional

import torch
from torch.utils.data import Dataset

from data.corpus import load_corpus_jsonl
from data.schema import Document
from tokenizer import BPETokenizer


class CorpusDataset(Dataset):
    """PyTorch Dataset over corpus: each item is a tensor of context_len token ids."""

    def __init__(
        self,
        corpus_path: str | Path,
        tokenizer: BPETokenizer,
        context_len: int,
        stride: Optional[int] = None,
        use_tier_tags: bool = False,
        use_truth_base_mixing: bool = False,
        truth_base_path: Optional[str | Path] = None,
    ):
        self.tokenizer = tokenizer
        self.context_len = context_len
        self.stride = stride or context_len
        self.use_tier_tags = use_tier_tags
        self.use_truth_base_mixing = use_truth_base_mixing
        self.fact_prefixes: list[list[int]] = []
        self.chunks: list[list[int]] = []
        docs = load_corpus_jsonl(corpus_path)
        all_ids: list[int] = []
        for doc in docs:
            text = doc.text
            if use_tier_tags:
                text = "[USER]\n" + text
            ids = tokenizer.encode(text)
            all_ids.extend(ids)
            eos_id = tokenizer.vocab.get("<|eos|>")
            if eos_id is not None:
                all_ids.append(eos_id)
        for i in range(0, len(all_ids) - context_len, self.stride):
            self.chunks.append(all_ids[i : i + context_len])
        if use_truth_base_mixing and truth_base_path:
            _path = Path(truth_base_path)
            if _path.exists():
                try:
                    from base.truth_base import load_truth_base
                    statements = load_truth_base(_path)
                    statements = [s for s in statements if s.tier <= 2]
                    for j in range(0, len(statements), 2):
                        batch = statements[j : j + 2]
                        block = "[FACT]\n" + "\n".join(s.text for s in batch) + "\n\n"
                        self.fact_prefixes.append(tokenizer.encode(block))
                except Exception:
                    pass

    def __len__(self) -> int:
        return len(self.chunks)

    def __getitem__(self, idx: int) -> torch.Tensor:
        chunk = list(self.chunks[idx])
        if self.use_truth_base_mixing and self.fact_prefixes and random.random() < 0.2:
            prefix = random.choice(self.fact_prefixes)
            combined = prefix + chunk
            chunk = combined[: self.context_len]
            if len(chunk) < self.context_len:
                chunk = chunk + [0] * (self.context_len - len(chunk))
        return torch.tensor(chunk, dtype=torch.long)
