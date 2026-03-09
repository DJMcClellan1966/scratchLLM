# Integration: CLI JSON and local API

Two ways to integrate scratchLLM's formal-only Q&A into other systems (EHR, legal tools, internal portals): **CLI with JSON output** and an optional **local HTTP API**.

## 1. CLI with JSON output (recommended)

Invoke `run_fast_response` with `--format json` and parse stdout (or write to a file with `--output`).

**Example:**

```bash
python scripts/run_fast_response.py --vertical medical --query "What is the guideline for X?" --format json
```

**Output** (single JSON object to stdout):

```json
{
  "response": "...",
  "citation_ids": [123, 456],
  "tiers": [0, 1],
  "audit": {
    "query": "What is the guideline for X?",
    "response_text": "...",
    "citation_ids": [123, 456],
    "tiers": [0, 1],
    "consistency_checked": true,
    "consistent": true,
    "conflicting_pairs_count": 0,
    "vertical_id": "medical"
  }
}
```

**Write to file:**

```bash
python scripts/run_fast_response.py --vertical medical --query "What is X?" --format json --output response.json
```

Your tool can then read `response.json` and use `response`, `citation_ids`, and `audit` for display or compliance.

## 2. Local HTTP API

For in-process or web integration, run the local API server; it exposes a single endpoint.

**Start the server** (binds to 127.0.0.1 only by default):

```bash
python scripts/serve_api.py --port 8050
```

**POST /query**

- **URL:** `http://127.0.0.1:8050/query`
- **Method:** POST
- **Content-Type:** application/json
- **Body:**
  - `query` (required) — Question or lookup.
  - `vertical` (optional) — Preset id (e.g. medical, legal, compliance); uses default paths.
  - `truth_base` (optional) — Override path to truth base.
  - `ir` (optional) — Override path to IR JSONL.
  - `top_k` (optional, default 5) — Max statements to use.
  - `max_tier` (optional, default 2) — Max tier for retrieval.
  - `include_audit` (optional, default true) — Include audit blob in response.

**Example request:**

```bash
curl -X POST http://127.0.0.1:8050/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is X?", "vertical": "medical"}'
```

**Example response (200):**

```json
{
  "response": "...",
  "citation_ids": [...],
  "tiers": [...],
  "audit": { ... }
}
```

**Errors:** 400 (missing/invalid query or paths), 500 (server error). Response body is JSON with an `error` key.

The API does not serve static files or other routes; only POST /query is supported. Use 127.0.0.1 to keep the server local.
