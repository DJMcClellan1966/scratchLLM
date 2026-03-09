# Verticals: control, provenance, consistency

Verticals are **domain presets** (e.g. general, medical, legal) that supply default paths and tier semantics. The same app and engine run for every vertical; only the config (paths, `max_tier`, optional tier labels) changes. Control, provenance, and consistency behavior are unchanged.

## What verticals provide

- **Default paths** — `default_truth_base`, `default_ir` so you don’t have to pass `--truth-base` / `--ir` every time.
- **Default max tier** — Stricter or looser retrieval per domain (e.g. medical may keep `max_tier` at 2).
- **Optional tier names** — For display only (e.g. 0 = "guideline", 1 = "consensus" in medical). Numeric tiers in the engine stay the same.
- **Optional source-to-tier** — (Future) Map source IDs to tiers per vertical when building corpus or loading IR.

## Config file

**Location:** `config/verticals.json`

**Schema per vertical:**

- `id` — string (e.g. `"general"`, `"medical"`, `"legal"`).
- `label` — display name (e.g. "General", "Medical", "Legal").
- `default_truth_base` — path or `null`.
- `default_ir` — path or `null`.
- `default_max_tier` — int (e.g. 2).
- `tier_names` — optional `{ "0": "necessary", "1": "guideline", ... }` for UI/display only.
- `source_to_tier` — optional `{ "source_id": 0, ... }` for future use; not used in the first cut.

Paths in the config are relative to the project root unless absolute.

## How to add a vertical

1. Open `config/verticals.json`.
2. Add a new key (e.g. `"finance"`) with the same structure as `general` or `medical`:
   - `id`, `label`, `default_truth_base`, `default_ir`, `default_max_tier`
   - Optionally `tier_names` and `source_to_tier`.
3. Save. The CLI and GUI will pick it up (GUI dropdown and `--vertical finance`).

## Running with a vertical

**CLI**

- **Fast response:**  
  `python scripts/run_fast_response.py --vertical medical --query "What is X?"`  
  Uses medical defaults for truth base and IR unless you pass `--truth-base` or `--ir` (explicit args override).
- **Inference:**  
  `python scripts/run_inference.py --vertical medical --use-base --prompt "..."`  
  Same: `--vertical` sets default truth base, IR, and `max_tier`; explicit flags override.
- **Consistency check:**  
  `python scripts/check_consistency.py --vertical medical`  
  Uses the vertical’s default truth base and IR paths.

**GUI**

- Choose a vertical from the **Vertical** dropdown. Truth base and IR path fields (and max tier) are pre-filled from that vertical’s config. You can still edit the paths before running.

## Overrides

Whenever you pass `--truth-base`, `--ir`, or `--max-tier` explicitly, they override the vertical’s defaults. So you can combine a vertical with one-off paths, e.g.:

```bash
python scripts/run_fast_response.py --vertical medical --ir path/to/special_ir.jsonl --query "..."
```

## Control, provenance, consistency

- **Control** — Same scripts and options; vertical only changes where defaults come from.
- **Provenance** — Citations and Gödel IDs work as before; tier display uses the same numeric tiers (and optional tier names for display).
- **Consistency** — `check_consistency.py` and the in-app consistency check use the same Gödel formal system; only the paths (from vertical or overrides) change.
