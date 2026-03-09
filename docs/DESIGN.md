# Design: user-grounded local LLM

## Goal

Build a local LLM that is **about the user**. The model is trained on as much of their data as we can gather so that:

1. **Responses are grounded** in what they actually read, write, and care about.
2. **Hallucinations**, when they happen, are at least **grounded in the user**—wrong or invented details that still relate to their interests, history, and content, rather than generic or useless fabrications.

## Data we gather

Maximize signal about the user. Use:

- **Email** (exports, mbox, etc.) — what they discuss, how they write.
- **Browsing** — bookmarks, history, reading lists; optionally fetched content from URLs they saved.
- **Reading** — saved articles, Pocket/Instapaper-style exports, anything that indicates what they read.
- **Social media** — exports (posts, likes, follows) to capture interests and style.
- **Local text** — notes, docs, messages, any text files on their machine they choose to include.

Inferred signals (e.g. bookmark titles + URLs, folder names) count as data. Fetched content from their URLs is allowed when used only to enrich the corpus for this local model.

## Why not use an API LLM?

- **Use allowance** — rate limits, daily caps.
- **Cost** — per-token or subscription; scales with use.
- **Size / capability limits** — what you can send, what you can get.
- **Internet** — no offline; dependency on someone else’s service.

A local, user-based model avoids those. One-time cost is compute and effort; ongoing cost is just your own machine.

## Why “ground on the user”?

Generic LLMs are trained on huge, mixed corpora. They often:

- **Hallucinate** — invent facts, links, or next steps that sound plausible but are wrong or useless.
- **Lead nowhere** — suggest things that don’t match your tools, your data, or your context.

A model trained mainly on **this user’s** data has a prior that is **their** interests, **their** vocabulary, **their** topics. Wrong or fuzzy answers are still more likely to stay in that space, so the output is more useful and easier to sanity-check against what the user actually has and does.

## Formal layer and design principles

The truth base, meaning language, and consistency machinery follow two principles that keep the system interpretable and robust:

- **Grounding (Tarski-inspired):** We do not define “truth” inside the system itself. Instead we use **tiers** (necessary, empirical, contingent, …) and **sources** as external grounding. Answers are “supported by these axioms” or “tier N,” not “true” in an undefinable sense. The app never claims a self-referential truth predicate.

- **Conflict handling (paraconsistent-inspired):** When axioms conflict (same subject, different object in the meaning layer), we **warn** and optionally **resolve** by tier; we do **not** let “one contradiction” imply “everything follows.” So the system remains useful and auditable even when the knowledge base is not perfectly consistent.

Retrieval can use **lightweight** extra signals: prefer **shorter** definitions when scores tie (simplicity), and optionally boost by **importance** (e.g. from pattern stats: terms used in many definitions). These are tie-breakers only, not full Kolmogorov or information-theory machinery.

## Implications for the repo

- **Data pipeline** should be built to pull in email, browsing, reading, social, and local text (and fetched content where we allow it).
- **Model scale** should follow corpus size (actual + inferred) so we don’t overfit or underuse the data.
- **Inference** stays local; no calls to cloud LLM APIs. The “brain” is always the model trained on the user’s data, running on their machine.
