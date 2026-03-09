# Align Product Spec

Align is one app that becomes the helper the user asked for: e.g. "help reading the bible daily", "plan a hike", "daily yoga". User states intent → quick corpus + vertical match → UI reflects that vertical (theme, copy, actions). All local after creation. Optional content from the dictionary repo (and app-forge if applicable) when building helpers.

---

## Vision and positioning

- **Intent in** — User describes what they want help with in one sentence.
- **Quick corpus + vertical match** — Intent is matched to a template (e.g. bible-daily, hike, yoga, journaling); a small truth base is generated and saved under `corpus/user_helpers/<id>/`. Optional: merge in content from dictionary/IR.
- **UI reflects vertical** — Header, placeholder, optional theme (accent color, welcome headline) and default actions (e.g. "Today's reading", "Reflect") so the app feels tailored to the type (bible vs hike vs yoga).
- **Local-first** — After creation, the app runs on-device with no internet required unless the user asks for more.

---

## Common self-help schema

A minimal schema shared across lifestyle/self-help verticals (documented here; v1 uses existing truth base fields):

| Slot | Description | Current mapping |
|------|-------------|-----------------|
| **Daily prompt / focus** | One thing to do or focus on today. | Statements with `category` = vertical; tip-style text. |
| **Tips** | Short, actionable statements. | Template `statements` (already in intent_templates). |
| **Reflection** | Prompt or question for reflection. | Statements with reflection-style text; optional `default_actions` e.g. "Reflect". |
| **Progress / tracking** | Optional "log" or "mark done". | Phase 2; not required for v1. |

No new schema file or DB for v1; truth base `statements` with `category` and `source` express these roles. Templates define the statements; optional `default_actions` in config drive preset queries (e.g. "Give me a reflection prompt").

---

## Verticals

### Lifestyle (first wave)

- **bible-daily** — Daily reading, devotional, scripture; reflection prompts; optional dictionary definitions for key terms.
- **hike** — Gear, trails, safety; already in intent_templates.
- **yoga** — Practice, breathwork, sequences; added in build.
- **journaling** — Prompts, structure, ideas; already in intent_templates.
- **goals / general** — Goals, steps, review; general template.

Each vertical has: intent keywords, template (statements), theme (label, placeholder, optional `welcome_headline`, `accent_color`, `default_actions`).

### Prebuilt vs intent-created

- **Prebuilt** — Vertical with default truth_base/IR paths (e.g. medical, legal in verticals.json). User picks from "explore sample".
- **Intent-created** — User phrase → template match → generated truth base in `corpus/user_helpers/<id>/`. Both can share the same theme/copy config.

### Other directions (spec only; not in first build)

- **Social / content** — e.g. "help me post consistently", "content calendar", "writing for social". Same pattern: intent → template → theme; add when needed.
- **Other** — Anything that fits "describe what you want help with" and passes guardrails.

---

## Dictionary / app-forge

- **Dictionary repo** ([github.com/DJMcClellan1966/dictionary](https://github.com/DJMcClellan1966/dictionary)): Use as a content source when building a helper. E.g. bible-daily: merge template statements + dictionary definitions (from already-ingested IR in this repo, e.g. `corpus/rag_ir.jsonl` or a slice). No live fetch from GitHub; consume pre-ingested content.
- **App-forge** — Align is the forge: one codebase, many verticals, each forged from intent + vertical template + optional content (dictionary, prebuilt pack). If app-forge is a separate repo, treat as optional content/template source.

---

## UI/UX rules

- **Welcome** — One question, one input, Get started; optional "explore sample" and "open existing helper".
- **Working view** — Header = vertical display label; ask box placeholder = vertical placeholder; optional 1–2 default action buttons (e.g. "Today's reading", "Reflect") that send preset queries.
- **Theming** — Per-vertical optional `accent_color`, `welcome_headline`; apply in GUI so "bible" feels different from "hike" or "yoga".

---

## First vertical: bible-daily

- **Intent keywords** — e.g. "bible", "daily reading", "devotional", "scripture", "read the bible".
- **Template** — In [config/intent_templates.json](config/intent_templates.json): `bible_daily` with statements for daily reading habit, reflection prompts, simple tips. Optional `merge_ir` / `merge_truth_base` to add dictionary content.
- **Theme** — Calm colors; `welcome_headline`; `default_actions`: e.g. "Today's reading", "Reflect".
- **Content** — From intent_templates; optionally from dictionary (already-ingested IR in this repo).

---

## Future verticals

- **Lifestyle (first wave)** — bible-daily, hike, yoga, journaling, goals/general are implemented first; same schema and theming pattern.
- **Social media / content** — "Help me post consistently", "content calendar", "writing for social". Same intent → template → theme pattern; add when needed.
- **Other lifestyle or productivity** — Any vertical that fits the common schema and guardrails.

---

## References

- [docs/INTENT.md](INTENT.md) — Intent flow, CLI, guardrails, templates.
- [docs/ROADMAP_PERSONAL_AI.md](ROADMAP_PERSONAL_AI.md) — Phased roadmap (refine with user, import, monetization).
- [docs/VERTICALS.md](VERTICALS.md) — Vertical config format and prebuilt verticals.
