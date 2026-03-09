# Roadmap: Personal AI App (Intent-Driven + Prebuilt)

A phased plan: **primary** = user states what they want → app builds a quick corpus (web/AI once) → run locally; **secondary** = prebuilt verticals for users looking for ideas. App refines with the user over time so it becomes *their* app.

---

## Principles

- **Intent-driven first** — User describes the helper they want (“I want to junk journal,” “I’m going on a hike here”). App creates a tailored corpus from that; no fixed vertical required.
- **Prebuilt for explorers** — Users who don’t know what they want can browse prebuilt verticals (ideas, discovery).
- **Web once, then local** — Use the web (and optional AI) to build or refine the corpus; after that the app runs on-device with no internet unless the user asks for more.
- **AI as refinement helper** — Optional AI step to clarify intent so the quick corpus better matches what the user wants.
- **Guardrails** — Only support legal, moral uses; reject or redirect the rest.
- **Reflect the user** — Work with the user to refine goals and content so the app becomes theirs over time.

---

## Phase Overview

| Phase | Focus | Duration (rough) |
|-------|--------|-------------------|
| 0 | Foundation (current) | Done |
| 1 | Intent flow + quick corpus + guardrails; prebuilt as secondary (v0) | 2–3 months |
| 2 | Refine with user; app reflects them (v1) | 1–2 months |
| 3 | Import + multi-helper (v2) | 1–2 months |
| 4 | Monetization + store (v3) | 1–2 months |
| 5 | Scale + optional cloud (v4+) | Ongoing |

**Target:** Shipped app where users describe what they want → get a quick corpus → use it locally; prebuilt available for explorers. Then refine with user so the app reflects them.

---

## Phase 0: Foundation

**Scope:** scratchLLM as it stands today.

**Deliverables:**
- Verticals (config + paths), formal-only Q&A, truth base + IR, citations, consistency.
- Engine runs with `--vertical X` or explicit paths and returns cited answers.

**Exit:** Ready to add intent flow and quick corpus on top.

---

## Phase 1: Intent Flow + Quick Corpus (v0)

**Goal:** User states what they want (nothing illegal/immoral) → app builds a quick corpus → they use it locally. Prebuilt verticals available for users looking for ideas.

### 1.1 Guardrails
- Check user intent (blocklist, simple rules, or classifier) before building a corpus.
- Refuse to build for illegal or immoral uses; optional “report if unsure” path.

### 1.2 Intent → quick corpus
- **Input:** Free text, e.g. “I want to junk journal” or “I’m going on a hike here.”
- **Output:** A small truth base (statements) tailored to that intent.
- **Ways to build (start simple):**
  - **Templates:** Map intent (keywords) to canned statement sets (e.g. “junk journal” → prompts, structure, tips).
  - **Generic fallback:** Turn the user’s phrase into a minimal corpus (e.g. goals, prompts) when no template matches.
  - **Optional:** One-time web or AI call to generate/refine statements; then save and run local.

### 1.3 User helpers storage
- Each “helper” = one user-declared intent + generated corpus. Store under e.g. `corpus/user_helpers/<id>/` with `truth_base.jsonl` and optional `meta.json` (intent, created date).
- App can list helpers and use one as the active knowledge source.

### 1.4 Prebuilt as secondary
- Keep existing verticals (medical, legal, compliance, general). In UI: “Describe what you want” (primary) vs “Use a prebuilt vertical” (explore/ideas).
- Prebuilt = curated packs for users who prefer to browse rather than describe.

### 1.5 App shell (v0)
- **Primary path:** “What do you want help with?” → user types intent → guardrails → quick corpus created → main screen uses that corpus (and optional user layer) for Q&A. All local after creation.
- **Secondary path:** “Explore prebuilt” → choose vertical → same Q&A with that vertical’s paths.
- Optional: “Add more” or “Refine” later (Phase 2) to pull in web/AI again if the user asks.

### 1.6 Exit
- User can describe a helper → get a quick corpus → use it on-device. Explorers can use prebuilt. Guardrails in place.

---

## Phase 2: Refine With User (v1)

**Goal:** App works with the user to refine goals and content so it becomes *their* app and reflects them.

### 2.1 User layer and profile
- User-specific facts: goals, constraints, logs, preferences. Stored with the helper or in a shared user layer.
- Optional structured profile (goals, level, preferences) used to filter/rank and to show “based on your goal.”

### 2.2 Refinement flow
- “Refine my helper”: optional AI or structured prompts to clarify intent → add or adjust statements.
- Logs and feedback (e.g. “this was useful” / “not what I meant”) feed back into user layer or corpus updates (e.g. add inferred preferences as statements).

### 2.3 “What should I do?” / “Suggest something”
- User asks for a suggestion or next step. Retrieval uses curated + user layer + profile; response cites “your goal” and “your history” where relevant.

### 2.4 Exit
- App adapts to the user over time; answers and suggestions reflect their goals and history.

---

## Phase 3: Import + Multi-Helper (v2)

**Goal:** Users add their own content via import; multiple helpers (intent-created or prebuilt) can coexist.

### 3.1 Import
- Format: markdown or CSV (e.g. subject, definition) → statements into user layer or “My content” for the active helper.
- UI: Import → preview → add to knowledge.

### 3.2 Multi-helper
- User can have several helpers (e.g. “junk journal,” “hike in Colorado”). Switch between them; each has its own corpus + optional user slice.
- List and choose active helper; prebuilt verticals remain an option.

### 3.3 Exit
- Users can import content and use multiple helpers; prebuilt and intent-created live in the same app.

---

## Phase 4: Monetization + Store (v3)

**Goal:** Sustainable model: free core + paid options; optional storefront.

### 4.1 Pricing
- Free: one intent-built helper + prebuilt exploration (or limited). Paid/Pro: more helpers, import, “refine with AI,” or premium prebuilt packs.

### 4.2 Storefront
- Catalog: prebuilt packs and/or “intent templates” (e.g. “Junk journal,” “Day hike”) that enrich the quick corpus when the user says something similar.
- Purchase → download pack or unlock template; app installs and uses it.

### 4.3 Exit
- Clear revenue path; store delivers value for both “I know what I want” and “I’m exploring” users.

---

## Phase 5: Scale + Optional Cloud (v4+)

**Goal:** More templates and prebuilt packs; optional cloud for heavy refinement or backup; on-device remains default.

- More intent templates and prebuilt verticals.
- Optional AI-assisted refinement (cloud) when user asks to “improve my helper.”
- Optional encrypted backup of profile + user layer; restore on new device.
- Partner or community packs in store.

---

## Dependencies

- Phase 1 depends on Phase 0 (engine + verticals).
- Phase 2 depends on Phase 1 (user layer + refinement flow).
- Phase 3 can overlap Phase 2 (import early).
- Phase 4 depends on 1–3 (something to sell and deliver).
- Phase 5 is incremental after 4.

---

## Success Metrics

| Phase | Metrics |
|-------|--------|
| 1 | Intent submissions; quick corpus created; use without internet; prebuilt usage |
| 2 | Refinement usage; “What should I do?” usage; retention |
| 3 | Import usage; multi-helper usage |
| 4 | Conversion to paid/Pro; store delivery success |
| 5 | More templates/packs; revenue and retention |

---

# Phase Breakdown (Detailed)

Task-level breakdown. Adjust order and ownership to your team.

---

## Phase 1 Breakdown: Intent Flow + Quick Corpus (v0)

### Week 1–2: Guardrails and quick corpus

| # | Task | Owner | Notes |
|---|------|--------|------|
| 1.1 | Define guardrails (blocklist, rules); implement check before corpus build | Eng | Legal/moral only |
| 1.2 | Define intent templates: keywords → statement sets (e.g. journaling, hiking, generic) | Content/Eng | 2–3 templates to start |
| 1.3 | Implement intent → template selection + generic fallback | Eng | No web/AI required for v0 |
| 1.4 | User helpers storage: create helper dir, write truth_base.jsonl + meta.json | Eng | corpus/user_helpers/<id>/ |
| 1.5 | CLI or API: create_helper_from_intent(intent, out_dir) → helper id/path | Eng | Script + callable |

### Week 3–4: App shell (primary + secondary)

| # | Task | Owner | Notes |
|---|------|--------|------|
| 1.6 | UI: “What do you want help with?” → intent input → Create helper | Eng | Calls quick corpus + save |
| 1.7 | UI: After create, set active helper and use its truth base for Q&A | Eng | Same engine as today |
| 1.8 | UI: “Use prebuilt” path — vertical dropdown (existing); use that vertical’s paths | Eng | Secondary path |
| 1.9 | Optional: “List my helpers” and switch active helper | Eng | Single helper v0 is OK |
| 1.10 | No internet required after corpus creation; document behavior | Eng/Docs | |

### Week 5–6: Polish and release

| # | Task | Owner | Notes |
|---|------|--------|------|
| 1.11 | Copy and onboarding: intent-first vs explore prebuilt | Product | |
| 1.12 | Error handling; guardrail rejection message | Eng | |
| 1.13 | Beta release; gather feedback | Product | |

**Phase 1 exit criteria:** User can describe a helper → get quick corpus → use it locally; prebuilt available; guardrails in place.

---

## Phase 2 Breakdown: Refine With User (v1)

| # | Task | Owner | Notes |
|---|------|--------|------|
| 2.1 | User profile schema (goals, constraints, preferences); store with helper or shared | Eng | |
| 2.2 | “Refine my helper”: optional AI or prompts to clarify intent; add/update statements | Eng | |
| 2.3 | User layer: logs and feedback → statements; retrieval uses them | Eng | |
| 2.4 | “What should I do?” / “Suggest” using profile + history + corpus | Eng | |
| 2.5 | Citations and UI: “based on your goal,” “your history” | Eng | |

**Phase 2 exit criteria:** App refines with user; answers reflect their goals and history.

---

## Phase 3 Breakdown: Import + Multi-Helper (v2)

| # | Task | Owner | Notes |
|---|------|--------|------|
| 3.1 | Import format (markdown/CSV) → statements; UI import + preview | Eng | |
| 3.2 | Multi-helper: list, switch, per-helper corpus + user slice | Eng | |
| 3.3 | Prebuilt and intent-built helpers in same list or tabs | Eng | |

**Phase 3 exit criteria:** Import works; multiple helpers; prebuilt and intent-built coexist.

---

## Phase 4 Breakdown: Monetization + Store (v3)

| # | Task | Owner | Notes |
|---|------|--------|------|
| 4.1 | Pricing: free vs Pro (helpers, import, refine, premium packs) | Product | |
| 4.2 | Storefront: prebuilt and/or intent templates; purchase → install pack | Eng | |
| 4.3 | In-app paywall or upgrade path | Eng | |

**Phase 4 exit criteria:** Revenue path clear; store can deliver packs/templates.

---

## Phase 5 Breakdown: Scale + Optional Cloud (v4+)

| # | Task | Owner | Notes |
|---|------|--------|------|
| 5.1 | More intent templates and prebuilt packs | Content/Eng | |
| 5.2 | Optional cloud refinement and backup | Eng | |
| 5.3 | Partner/community packs; metrics and iteration | Product | |

---

## Summary

- **Primary:** User states what they want → guardrails → quick corpus (templates + optional web/AI) → use locally. Prebuilt = **secondary** for explorers.
- **Later:** Refine with user, import, multi-helper, monetization, scale.
- **Next step:** Implement Phase 1: guardrails, intent templates, quick corpus, user helpers storage, and UI (intent + prebuilt).
