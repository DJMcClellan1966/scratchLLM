"""Dataset: read corpus, tokenize, yield fixed-length chunks for training."""
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
    ):
        self.tokenizer = tokenizer
        self.context_len = context_len
        self.stride = stride or context_len
        self.chunks: list[list[int]] = []
        docs = load_corpus_jsonl(corpus_path)
        all_ids: list[int] = []
        for doc in docs:
            ids = tokenizer.encode(doc.text)
            all_ids.extend(ids)
            # Optional: add EOS between docs
            eos_id = tokenizer.vocab.get("<|eos|>")
            if eos_id is not None:
                all_ids.append(eos_id)
        for i in range(0, len(all_ids) - context_len, self.stride):
            self.chunks.append(all_ids[i : i + context_len])

    def __len__(self) -> int:
        return len(self.chunks)

    def __getitem__(self, idx: int) -> torch.Tensor:
        return torch.tensor(self.chunks[idx], dtype=torch.long)
