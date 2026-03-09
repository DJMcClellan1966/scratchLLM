# scratchLLM

A **local LLM built from scratch** (Sebastian Raschka's book) that is **based on the user**: it gathers as much information about them as possible—email, browsing, reading, social media—and trains on that corpus so responses are grounded in the user's own context.

## Why user-based and local

- **API LLMs are constrained** by use limits, cost, size caps, and internet dependency.
- **LLMs hallucinate** and often give answers that sound useful but lead nowhere.
- **Basing the model on the user** grounds responses in their real data (interests, history, writing). If the model hallucinates, at least it does so from the user's own material—not generic or irrelevant noise.

So: one model per user, trained on their data, running locally on their machine (CPU-first). No usage quotas, no per-token billing, no mandatory cloud.

## Stack

- **Local only** for the model: no cloud inference APIs; training and inference on your machine.
- **Data gathering** is broad: local text, email, social exports, bookmarks, reading lists, plus fetched content (e.g. from URLs) to enrich the corpus.
- See [docs/LOCAL_STACK.md](docs/LOCAL_STACK.md) and [docs/DESIGN.md](docs/DESIGN.md) for rules and rationale.

## Setup

```bash
cd scratchLLM
pip install -e .
# or: pip install torch requests beautifulsoup4
```

## Usage

Run from the project root (`scratchLLM/`).

**1. Build corpus** — Collect text from local sources (and optionally fetch URLs from bookmarks):

```bash
python scripts/build_corpus.py --out-dir corpus \
  --text path/to/notes path/to/docs \
  --email path/to/mail.mbox \
  --social path/to/twitter_export \
  --bookmarks path/to/Chrome/Bookmarks \
  --readings path/to/pocket_export.html
```

Use `--fetch-urls` to fetch article content from bookmark URLs (rate-limited). Output: `corpus/corpus.jsonl` and `corpus/manifest.json`.

**2. Train model** — Train a BPE tokenizer (if missing) and the GPT model. Model scale is derived from corpus size.

```bash
python scripts/train_model.py corpus --epochs 3
```

Checkpoints and `scale.json` are written to `corpus/checkpoints/`; the tokenizer is in `corpus/tokenizer/`.

**3. Run inference** — Generate text from a prompt (CLI or interactive):

```bash
python scripts/run_inference.py --checkpoint corpus/checkpoints/ckpt_final.pt --tokenizer corpus/tokenizer --prompt "Your prompt" --max-tokens 50
```

Omit `--prompt` for interactive mode.

**4. Fast build (no training)** — Answer from the formal layer only (truth base and/or IR). No checkpoint needed; runs on CPU.

```bash
python scripts/run_fast_response.py --query "What is X?" --truth-base base/truth_base.jsonl
# or with IR: --ir path/to/pregenerated_ir.jsonl
```

**GUI:** `python scripts/run_gui.py` — query box, truth-base/IR paths, options (top-k, show IDs/tiers), Run and Check consistency.

**Consistency check:** `python scripts/check_consistency.py --truth-base base/truth_base.jsonl` (or `--ir path/to/ir.jsonl`). Exit 0 if consistent, 1 if not.

Use `--vertical medical` or `--vertical legal` to use domain presets for default paths and max tier (see [docs/VERTICALS.md](docs/VERTICALS.md)).

**Unseen patterns:** `python scripts/analyze_axiom_patterns.py --ir corpus/rag_ir.jsonl --limit 10000 --out corpus/pattern_stats.json` to compute ambiguity per subject, definition-use graph, and definition templates. See [docs/PATTERNS.md](docs/PATTERNS.md).

See [docs/FAST_BUILD.md](docs/FAST_BUILD.md) for details. For richer answers, train a model and use `run_inference` with `--use-base --use-meaning`.

## Project structure

| Path | Purpose |
|------|--------|
| `config/scaling.py` | Compute model size (vocab, layers, etc.) from corpus stats |
| `data/` | Document schema, source loaders (text, email, social, bookmarks, readings), infer, fetch, corpus builder |
| `tokenizer/bpe.py` | BPE tokenizer: train, encode/decode, save/load |
| `model/` | GPT from scratch: causal attention, decoder blocks, LM head |
| `train/` | Dataset, train config, training loop (CPU-first) |
| `inference/generate.py` | Load checkpoint + tokenizer, autoregressive generation |
| `scripts/` | `build_corpus.py`, `train_model.py`, `run_inference.py`, `run_fast_response.py`, `run_gui.py`, `check_consistency.py`, `analyze_axiom_patterns.py` |
| `base/respond.py` | Formal-only response (no model): `respond_formal_only` |
| `docs/FAST_BUILD.md` | Fast-build path: formal language + truth base/IR, local/CPU |
