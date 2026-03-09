# Hero verticals: Medical, Legal, Compliance

Three **hero verticals** are first-class presets for domain-specific, local, auditable Q&A with control, provenance, and consistency. Use them when you need answers grounded in guidelines, law, or policy with citations and optional consistency checks.

See [docs/VERTICALS.md](VERTICALS.md) for generic vertical config (adding your own vertical, schema).

---

## Medical

**Purpose:** Local, auditable Q&A over clinical guidelines, consensus statements, and practice material. No patient data in the model; use for reference and support only.

**Tier semantics (display):**

| Tier | Name |
|------|------|
| 0 | guideline |
| 1 | consensus |
| 2 | practice |
| 3 | inference |
| 4 | contested |
| 5 | opinion |
| 6 | speculation |

**Where to put content:**

- Truth base: `corpus/medical_truth_base.jsonl` (one statement per line; same format as [base/truth_base](base/truth_base)).
- IR: `corpus/medical_ir.jsonl` (subject, definition, optional relations/examples; same as other IR JSONL).

**How to run:**

```bash
python scripts/run_fast_response.py --vertical medical --query "What is the guideline for X?"
python scripts/run_gui.py   # select Medical in the Vertical dropdown
python scripts/generate_compliance_report.py --vertical medical --format text
```

**Content packs:** Export your guidelines or consensus docs into the statement/IR format and drop the file at the default path. You can also use `--truth-base` / `--ir` to point to custom paths while still using medical tier names and defaults.

---

## Legal

**Purpose:** Local, auditable Q&A over statutes, precedent, and commentary. Supports citation and consistency checks for research and internal use.

**Tier semantics (display):**

| Tier | Name |
|------|------|
| 0 | statute |
| 1 | precedent |
| 2 | commentary |
| 3 | inference |
| 4 | contested |
| 5 | opinion |
| 6 | speculation |

**Where to put content:**

- Truth base: `corpus/legal_truth_base.jsonl`
- IR: `corpus/legal_ir.jsonl`

**How to run:**

```bash
python scripts/run_fast_response.py --vertical legal --query "What does statute X say?"
python scripts/run_gui.py   # select Legal in the Vertical dropdown
python scripts/check_consistency.py --vertical legal
```

**Content packs:** Structure your statutes, case summaries, or commentary as IR JSONL (subject, definition, optional relations) and place at the default paths, or override with `--truth-base` / `--ir`.

---

## Compliance

**Purpose:** Local, auditable Q&A over internal policy, procedures, and guidance. Suited to compliance and risk teams who need traceable answers and consistency reports.

**Tier semantics (display):**

| Tier | Name |
|------|------|
| 0 | policy |
| 1 | procedure |
| 2 | guidance |
| 3 | inference |
| 4 | contested |
| 5 | opinion |
| 6 | speculation |

**Where to put content:**

- Truth base: `corpus/compliance_truth_base.jsonl`
- IR: `corpus/compliance_ir.jsonl`

**How to run:**

```bash
python scripts/run_fast_response.py --vertical compliance --query "What is the policy on X?"
python scripts/run_gui.py   # select Compliance in the Vertical dropdown
python scripts/generate_compliance_report.py --vertical compliance --output report.json
```

**Content packs:** Export policies and procedures into the same statement/IR format; place at the default paths or pass explicit `--truth-base` / `--ir`. Use the compliance report for auditors.

---

## Default paths are placeholders

The hero verticals point to paths like `corpus/medical_truth_base.jsonl` by default. Those files are not shipped; create them or copy sample content so that `--vertical medical` (or legal/compliance) finds data. To try without content, use explicit paths to existing truth base or IR files.
