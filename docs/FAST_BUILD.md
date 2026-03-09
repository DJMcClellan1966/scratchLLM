# Fast build (no training)

Use the **formal language** (meaning structs, tiers, relations) and **Gödel encoding** to get LLM-like Q&A **without training a model**. Ideal for local/CPU and quick setup.

## When to use

- You have a **truth base** (e.g. `base/truth_base.jsonl`) or **IR JSONL** (e.g. dictionary `pregenerated_ir.jsonl`) but no checkpoint yet.
- You want **definition-like** or short factual answers with **zero** training and **no** model load.
- You want **interpretability**: optional Gödel IDs of the statements used for each answer.

## How to run

From the project root:

```bash
python scripts/run_fast_response.py --query "What is recursion?" --truth-base base/truth_base.jsonl
```

With IR (e.g. dictionary pregenerated IR):

```bash
python scripts/run_fast_response.py --query "What is bytecode?" --ir path/to/pregenerated_ir.jsonl
```

With both truth base and IR (merged):

```bash
python scripts/run_fast_response.py --query "What is X?" --truth-base base/truth_base.jsonl --ir path/to/pregenerated_ir.jsonl --top-k 5 --show-ids
```

**Options:**

- `--query` — Question or lookup (required).
- `--truth-base` — Path to truth_base.jsonl.
- `--ir` — Path to IR JSONL (subject, definition, relations, examples).
- `--top-k` — Max statements to use (default 5).
- `--max-tier` — Max tier 0–2 for retrieval (default 2); lower = stricter.
- `--no-resolve` — Skip conflict resolution by tier.
- `--show-ids` — Print Gödel numbers of statements used.
- `--show-tiers` — Print each statement with its tier label.
- `--check-consistency` — Warn if truth base/IR is inconsistent before responding.
- `--limit` — Use only first N lines of IR (for consistency check on large files).
- `--importance` — Path to pattern_stats.json (or directory containing definition_use_in_degree.json) from `analyze_axiom_patterns.py`; used as a tie-breaker so terms that appear in many definitions rank slightly higher when scores tie.
- `--format json` — Output a single JSON object with `response`, `citation_ids`, `tiers`, and `audit` (for integration). Use with `--output file.json` to write to a file.
- `--audit` — Include audit blob: print "Audit: N citations, consistency: yes/no" after the response; with `--format json` the full audit is in the JSON.
- `--output` — When `--format json`, write JSON to this file instead of stdout.

No checkpoint, no tokenizer: runs on CPU only.

**Audit blob:** For compliance and integration, use `--audit` or `--format json`. The audit records query, response, citation IDs, tiers, and optional KB consistency result. See [docs/AUDIT.md](AUDIT.md).

**Integration:** Use `--format json` for CLI integration (see [docs/API.md](API.md)). For a local POST /query endpoint, run `python scripts/serve_api.py --port 8050` (binds to 127.0.0.1). See [docs/API.md](API.md).

**Intent-driven helper (primary):** Say what you want (e.g. "I want to junk journal" or "I'm going on a hike"). The app builds a quick corpus from templates (see `config/intent_templates.json`), saves it under `corpus/user_helpers/<id>/`, and you use it locally. Guardrails block illegal/immoral intents. CLI: `python scripts/create_helper_from_intent.py "I want to junk journal"`.

**GUI:** Run `python scripts/run_gui.py`: **What do you want help with?** (create a helper from intent) or pick a **Helper** (My helpers or Prebuilt verticals). Then query, truth-base/IR paths, top-k, Show IDs/tiers, Run and Check consistency.

**Consistency:** Run `python scripts/check_consistency.py --truth-base path/to/truth_base.jsonl` (and/or `--ir path/to/ir.jsonl`). Exit 0 if consistent, 1 if not. Use `--limit N` for large IR files.

**Compliance report:** Run `python scripts/generate_compliance_report.py --vertical medical` (or `--truth-base` / `--ir`) to produce a report with KB consistency, axiom count, and tier breakdown. Use `--format text` for a short summary or `--format json` (default) for machine-readable output; `--output path.json` writes to a file. Suitable for auditors.

**Import rag_definitions.json:** To use a large keyword/definition JSON (e.g. desktop dictionary `rag_definitions.json`), run `python scripts/import_rag_definitions.py --input path/to/rag_definitions.json --output corpus/rag_ir.jsonl --limit 50000`, then use `--ir corpus/rag_ir.jsonl` (and `--limit` for consistency checks on big files).

## What it does

1. Loads statements from the truth base and/or IR (truth base first, then IR).
2. Parses your query into the formal meaning language (e.g. QUERY, BE, PRED).
3. Retrieves top-k statements by meaning overlap and word overlap.
4. Optionally resolves conflicts by tier (keeps higher-certainty statements).
5. Returns the concatenated statement texts as the answer, and optionally the Gödel IDs of the statements used.

So the **formal layer** (keywords, definitions, relations, tiers) and **Gödel encoding** (consistency, statement IDs) are the backbone. No neural model is involved.

## Richer answers (with a model)

For more fluent or open-ended answers, train a small model and use RAG:

```bash
python scripts/train_model.py corpus --epochs 3
python scripts/run_inference.py --truth-base base/truth_base.jsonl --use-base --use-meaning --prompt "What is X?"
```

That path uses the same formal layer for retrieval and conflict resolution, but the model generates the final text.
