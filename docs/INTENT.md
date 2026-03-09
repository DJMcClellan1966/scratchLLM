# Intent-driven helper (primary path)

The app supports two ways to get a helper: **describe what you want** (primary) or **use a prebuilt vertical** (secondary). For the primary path, you state your intent in plain language; the app builds a quick corpus and uses it locally.

## Flow

1. **User states intent** — e.g. "I want to junk journal" or "I'm going on a hike here."
2. **Guardrails** — The app checks that the intent is legal and moral; it refuses to build a corpus for blocked terms.
3. **Quick corpus** — Intent is matched to a template (e.g. journaling, hiking in `config/intent_templates.json`) or the generic template. A small truth base (statements) is generated and saved under `corpus/user_helpers/<id>/truth_base.jsonl`.
4. **Use locally** — You run Q&A against that corpus (GUI or CLI). No internet required after creation.

## CLI

```bash
python scripts/create_helper_from_intent.py "I want to junk journal"
# Created helper: junk_journal
# Truth base: corpus/user_helpers/junk_journal/truth_base.jsonl
# Statements: 11

python scripts/run_fast_response.py --query "How do I get started?" --truth-base corpus/user_helpers/junk_journal/truth_base.jsonl
```

Options:

- `--out-dir` — Where to store helpers (default: `corpus/user_helpers`).
- `--templates` — Path to `intent_templates.json` (default: `config/intent_templates.json`).
- `--id` — Optional helper id/slug.

## GUI

In `run_gui.py`:

1. **What do you want help with?** — Type your intent and click **Create helper**. The new helper appears in the **Helper** dropdown and is selected.
2. **Helper** — Choose a **My:** helper (created from intent) or a **Prebuilt** vertical (General, Medical, Legal, Compliance). Paths are set automatically.
3. **Query** — Ask a question; the answer is grounded in the selected helper’s corpus.

## Templates

Templates live in `config/intent_templates.json`. Each template has:

- `id` — Template key (e.g. `journaling`, `hiking`, `general`).
- `label` — Display label.
- `keywords` — Phrases that match this template (e.g. "junk journal", "hike").
- `statements` — List of `{text, tier, source, category}` objects written to the truth base.

Matching is by keyword overlap with the user’s intent; if no template matches, the `general` template is used. You can add or edit templates to support new domains.

## Guardrails

`base/intent.check_guardrails()` blocks intents that contain terms from a blocklist (e.g. illegal, harm, fraud). Rejected intents raise `ValueError` with a short message. The blocklist is in `base/intent.py` (`_GUARDRAIL_BLOCKLIST`); you can override it when calling the API.

## API

From Python:

```python
from base.intent import check_guardrails, create_helper_from_intent, list_user_helpers

allowed, msg = check_guardrails("I want to junk journal")
# (True, "OK")

helper_id, truth_base_path, count = create_helper_from_intent(
    "I want to junk journal",
    out_dir="corpus/user_helpers",
)
# helper_id="junk_journal", truth_base_path=Path("corpus/user_helpers/junk_journal/truth_base.jsonl"), count=11

helpers = list_user_helpers("corpus/user_helpers")
# [{"helper_id": "junk_journal", "truth_base_path": "...", "intent": "I want to junk journal"}, ...]
```

## Roadmap

See [ROADMAP_PERSONAL_AI.md](ROADMAP_PERSONAL_AI.md): Phase 1 is intent flow + quick corpus; later phases add refinement with the user, import, and monetization.
