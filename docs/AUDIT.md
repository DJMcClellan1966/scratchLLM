# Audit blob (proof and compliance)

Every response can include an **audit blob**: a JSON-serializable object that records the query, response text, citation IDs (Gödel numbers), tiers of cited statements, and optional consistency-check result. Use it for integration, compliance, and auditing.

## Schema

When `include_audit=True` is passed to `respond_formal_only`, the 4th return value is a dict with:

| Key | Type | Description |
|-----|------|-------------|
| `query` | string | The question or lookup that was run. |
| `response_text` | string | The concatenated statement text returned. |
| `citation_ids` | list[int] | Gödel numbers of the statements used. |
| `tiers` | list | Tier number for each cited statement (same order as citation_ids). |
| `consistency_checked` | bool | Whether the knowledge base was checked for conflicts. |
| `consistent` | bool \| null | True if KB is consistent, False if conflicts found, null if not checked. |
| `conflicting_pairs_count` | int \| null | Number of conflicting axiom pairs (when consistency_checked). |
| `vertical_id` | string \| null | Vertical preset used (e.g. medical, legal), if any. |

## How to get the audit

**CLI (run_fast_response):**

- `--audit` — Print a one-line summary after the response: "Audit: N citations, consistency: yes/no".
- `--format json` — Output a single JSON object to stdout with `response`, `citation_ids`, `tiers`, and `audit`. Use for integration (e.g. pipe to another tool).
- `--output file.json` — When using `--format json`, write the JSON to a file instead of stdout.

Example for integration:

```bash
python scripts/run_fast_response.py --vertical medical --query "What is X?" --format json --output response.json
```

Then read `response.json`; the `audit` key contains the full blob.

**GUI (run_gui):**

- Check **Include audit (citations + consistency)**. When you run a query, the response area shows "Audit: N citations, consistency: yes/no" and the full audit dict is written to `last_audit.json` in the project root.

**Python API:**

- Call `respond_formal_only(..., include_audit=True, run_consistency_check=True)`. The 4th element of the return tuple is the audit dict (or `None` when `include_audit=False`).

## Consistency check in the audit

When `run_consistency_check=True` and at least one of `truth_base_path` or `ir_path` is set, the formal system runs a consistency check on the loaded axioms (no two axioms with conflicting meanings). The result is stored in the audit as `consistent` and `conflicting_pairs_count`. This supports compliance workflows where each response can carry a proof that the KB was checked.
