# Unseen patterns analytics

Run pattern analysis over IR or truth-base axioms to compute structure the app does not yet use at retrieval time: **ambiguity per subject**, **definition-use graph**, and **definition templates**. Outputs are JSON files for inspection and future use (e.g. ranking by ambiguity, or "primitives" from in-degree).

## How to run

From the project root:

```bash
python scripts/analyze_axiom_patterns.py --ir corpus/rag_ir.jsonl --limit 10000 --out corpus/pattern_stats.json
```

Or with a truth base:

```bash
python scripts/analyze_axiom_patterns.py --truth-base base/truth_base.jsonl --out corpus/pattern_stats.json
```

**Options:**

- `--ir` — Path to IR JSONL (subject, definition per line).
- `--truth-base` — Path to truth_base.jsonl (use exactly one of `--ir` or `--truth-base`).
- `--limit` — Max statements to load (recommended for quick runs; full pair-wise conflict is O(n²) in statements with meaning).
- `--out` — Output path. If it ends in `.json`, a single JSON file is written with keys `ambiguity_per_subject`, `definition_use_in_degree`, `definition_templates`. If it is a directory or path without `.json`, four files are written: `ambiguity_per_subject.json`, `definition_use_in_degree.json`, `definition_templates.json`, `definition_use_edges.jsonl`.

## Outputs

- **ambiguity_per_subject** — For each subject that appears in at least one conflicting pair (same type and subject, different object in the meaning layer), the count of conflicting pairs it appears in. High count = ambiguous or polysemous term. Can be used to down-rank or flag uncertain subjects in retrieval.
- **definition_use_in_degree** — For each subject, how many other definitions use it as a whole-word/phrase in their definition text. High in-degree = "primitive" or hub term (used to define many others). Pass the pattern_stats path as `--importance` to `run_fast_response.py` to use it as a tie-breaker in retrieval (higher in-degree ranks slightly higher when scores tie).
- **definition_templates** — Top 50 prefixes (first 30 chars or 6 words, normalized) of definition text and their counts. Surfaces common phrasal patterns (e.g. "a ... is", "the process of").
- **definition_use_edges** (when `--out` is a directory) — One JSONL line per edge `{"from": subject_used, "to": subject_being_defined}`. Use for graph analysis or visualization.

## Performance

- Use `--limit` (e.g. 10_000) for quick runs. Full ambiguity check over 50k statements with meaning is O(n²).
- Definition-use scan is one pass over statements; for each definition, whole-word match against the set of subjects (can be large).
