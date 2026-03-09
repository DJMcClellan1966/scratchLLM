# Intent-driven helper (primary path)

The app is a **blank canvas** by default: you describe what you want, and the helper starts with only that goal. The app grows from your input over time. You can also use a prebuilt vertical or (via CLI) a template with preset content.

## Flow

1. **User states intent** — e.g. "I want help reading the bible daily" or "I want to get into hiking."
2. **Guardrails** — The app checks that the intent is legal and moral; it refuses to build a corpus for blocked terms.
3. **Quick corpus** — By default the helper is **blank**: only your stated goal is saved (one statement). No preset template content. The truth base is saved under `corpus/user_helpers/<id>/truth_base.jsonl`. (CLI can use templates with `blank_canvas=False` to get preset statements.)
4. **Use locally** — You run Q&A against that corpus (GUI or CLI). Add goals and notes over time; the app uses what you add.

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

1. **Welcome** — App always opens on the welcome screen. **What do you want help with?** — Type your intent and click **Get started**. A new helper is created as a **blank canvas** (only your goal; no template content). The working view opens with a generic "Ask anything…" prompt.
2. **Or** — Use **Or open an existing helper** to open a previous canvas, or **Or explore a sample** to use a prebuilt vertical.
3. **Query** — Ask a question; the answer is grounded in the selected helper’s corpus (which you build over time for blank-canvas helpers).

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

# Blank canvas (default): only the goal statement
helper_id, truth_base_path, count = create_helper_from_intent(
    "I want to read the bible",
    out_dir="corpus/user_helpers",
    blank_canvas=True,
)
# count=1

# With template content (preset statements)
helper_id, truth_base_path, count = create_helper_from_intent(
    "I want to junk journal",
    out_dir="corpus/user_helpers",
    blank_canvas=False,
)
# count >= 1 (goal + template statements)

helpers = list_user_helpers("corpus/user_helpers")
# [{"helper_id": "junk_journal", "truth_base_path": "...", "intent": "I want to junk journal"}, ...]
```

## Roadmap

See [ROADMAP_PERSONAL_AI.md](ROADMAP_PERSONAL_AI.md): Phase 1 is intent flow + quick corpus; later phases add refinement with the user, import, and monetization.
