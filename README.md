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

**Create helper from intent (primary):** Describe what you want help with; the app builds a quick corpus and uses it locally. Nothing illegal or immoral.

```bash
python scripts/create_helper_from_intent.py "I want to junk journal"
# Creates corpus/user_helpers/<id>/truth_base.jsonl; use that path or the GUI.
```

**GUI:** `python scripts/run_gui.py` — **What do you want help with?** (create a helper from your intent) or choose a **Helper** (My helpers or Prebuilt verticals). Query, truth-base/IR paths, Run and Check consistency. After creating a helper, use it with no internet.

**Consistency check:** `python scripts/check_consistency.py --truth-base base/truth_base.jsonl` (or `--ir path/to/ir.jsonl`). Exit 0 if consistent, 1 if not.

Use `--vertical medical`, `--vertical legal`, or `--vertical compliance` for domain presets (see [docs/VERTICALS.md](docs/VERTICALS.md)). **Hero verticals** (medical, legal, compliance): [docs/HERO_VERTICALS.md](docs/HERO_VERTICALS.md).

**Compliance report:** `python scripts/generate_compliance_report.py --vertical medical` (or `--truth-base`/`--ir`) — consistency, axiom count, tier breakdown for auditors. See [docs/FAST_BUILD.md](docs/FAST_BUILD.md).

**Integration:** Use `--format json` with `run_fast_response` for machine-readable output, or run `python scripts/serve_api.py --port 8050` for a local POST /query API. See [docs/API.md](docs/API.md).

**Unseen patterns:** `python scripts/analyze_axiom_patterns.py --ir corpus/rag_ir.jsonl --limit 10000 --out corpus/pattern_stats.json` to compute ambiguity per subject, definition-use graph, and definition templates. See [docs/PATTERNS.md](docs/PATTERNS.md).

See [docs/FAST_BUILD.md](docs/FAST_BUILD.md) for details. For richer answers, train a model and use `run_inference` with `--use-base --use-meaning`.

**Roadmap:** [docs/ROADMAP_PERSONAL_AI.md](docs/ROADMAP_PERSONAL_AI.md) — intent-driven (primary): you describe what you want → quick corpus → use locally; prebuilt verticals (secondary) for exploring. Phases: refine with user, import, monetization.

## Project structure

| Path | Purpose |
|------|--------|
| `config/scaling.py` | Compute model size (vocab, layers, etc.) from corpus stats |
| `data/` | Document schema, source loaders (text, email, social, bookmarks, readings), infer, fetch, corpus builder |
| `tokenizer/bpe.py` | BPE tokenizer: train, encode/decode, save/load |
| `model/` | GPT from scratch: causal attention, decoder blocks, LM head |
| `train/` | Dataset, train config, training loop (CPU-first) |
| `inference/generate.py` | Load checkpoint + tokenizer, autoregressive generation |
| `scripts/` | `build_corpus.py`, `train_model.py`, `run_inference.py`, `run_fast_response.py`, `run_gui.py`, `create_helper_from_intent.py`, `check_consistency.py`, `analyze_axiom_patterns.py` |
| `base/intent.py` | Intent guardrails, quick corpus from templates, `create_helper_from_intent`, `list_user_helpers` |
| `config/intent_templates.json` | Templates (e.g. journaling, hiking) for intent → statements |
| `base/respond.py` | Formal-only response (no model): `respond_formal_only` |
| `docs/FAST_BUILD.md` | Fast-build path: formal language + truth base/IR, local/CPU |
