# Formal system (minimal)

A minimal **formal system** is defined over the Gödel numbering of scratchLLM objects. Formulas are natural numbers (Gödel numbers of Statements and, optionally, MeaningStructs). We use it for **consistency analysis** of the truth base. We do **not** (yet) prove incompleteness.

## What the formal system is

- **Formulas:** Natural numbers that are Gödel numbers of [base/truth_base.py](base/truth_base.py) `Statement`s. Optionally, with the meaning-extraction rule, formulas also include Gödel numbers of [base/language.py](base/language.py) meaning structs (BE/QUERY/PRED).
- **Axioms:** The set of Gödel numbers of every statement in a given truth base. Load with `load_axioms(truth_base_path)`.
- **Rules:** One optional rule — **meaning extraction:** from an axiom that decodes to a Statement with a `meaning` field, the Gödel number of that meaning struct is also a theorem. So theorems = axioms ∪ { encode_meaning(s.meaning) for each statement s with meaning }.
- **Proof:** A proof of formula g is a finite sequence ending in g where each step is an axiom or derived by a rule. With only meaning extraction, proofs are either one step (g is an axiom) or two steps (axiom statement → meaning).

## How to use

1. **Load axioms** from a truth base file:
   ```python
   from base.formal_system import load_axioms, get_theorems, is_consistent, conflicting_pairs
   axioms = load_axioms("base/truth_base.jsonl")
   ```

2. **Get theorems** (axioms plus meaning-derived formulas):
   ```python
   theorems = get_theorems(axioms, include_meaning_derivations=True)
   ```

3. **Check consistency** (no two axioms have conflicting meanings):
   ```python
   ok = is_consistent(axioms)
   if not ok:
       pairs = conflicting_pairs(axioms)  # list of (n, m) conflicting axiom pairs
   ```

4. **Use dictionary/ingestion IR** (e.g. pregenerated_ir.jsonl) as axioms via the IR bridge:
   ```python
   from base import load_axioms_from_ir, is_consistent, conflicting_pairs
   axioms = load_axioms_from_ir("path/to/pregenerated_ir.jsonl")
   print(is_consistent(axioms))
   ```
   Or run the script: `python scripts/run_godel_on_ir.py path/to/pregenerated_ir.jsonl`. For a quick demo on a large IR file use `--limit 100` (e.g. `python scripts/run_godel_on_ir.py path/to/ir.jsonl --limit 100`). Each IR record is converted to a Statement (meaning from the first relation: `is_a` → BE, else → PRED); then the same Gödel/consistency machinery applies.

5. **Check consistency of paths** (truth base and/or IR combined):
   ```python
   from base.formal_system import check_consistency_of_paths
   consistent, pairs = check_consistency_of_paths(truth_base_path="base/truth_base.jsonl", ir_path=None, ir_limit=None)
   ```
   CLI: `python scripts/check_consistency.py --truth-base base/truth_base.jsonl` (and/or `--ir path/to/ir.jsonl`). Exit 0 if consistent, 1 if not. Use `--limit N` for large IR files.

6. **Gate on save:** `save_truth_base(statements, path, check_consistency=True)` raises `ValueError` if the statement set is inconsistent (so callers can refuse to write).

## What we analyze

- **Consistency:** We check that no two axioms have conflicting meanings (same type and same subject/ref but different object, per [base/language.py](base/language.py) `conflict`). If the truth base has two statements that conflict, `is_consistent` returns False and `conflicting_pairs` returns those axiom pairs (by Gödel number).

We do **not** (yet) prove incompleteness or any meta-theorem about the system.

## What would be needed for an incompleteness-style result

1. **Formal system** — Done minimally: axioms = truth-base statements; one rule (meaning extraction); formulas = Gödel numbers.
2. **Consistency** — We can check it; we do not prove it. For an incompleteness argument the system must be consistent (or we get triviality).
3. **Sufficient strength** — The system would need to represent (e.g.) basic arithmetic so that Gödel’s self-referential sentence can be built. We do **not** have that; our formulas are Statements and meaning structs, not arithmetic.
4. **Recursive enumerability** — The set of theorems is r.e. (axioms are finite; the rule is computable). So we have this.

The gap for an incompleteness result is (3): we would need to define an interpretation of arithmetic in our formulas or extend the system so that it can represent arithmetic. That is out of scope for this minimal system.
