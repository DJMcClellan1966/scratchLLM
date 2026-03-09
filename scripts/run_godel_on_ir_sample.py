"""Run Gödel on first N lines of an IR file (for quick demo)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from base import load_axioms_from_ir, is_consistent, conflicting_pairs, get_theorems
from base.godel import decode_statement

def main():
    path = Path(r"C:\Users\DJMcC\OneDrive\Desktop\dictionary\dictionary\data\shannon\pregenerated_ir.jsonl")
    if not path.exists():
        print("Path not found:", path)
        return
    lines = path.read_text(encoding="utf-8").splitlines()[:100]
    tmp = ROOT / "corpus" / "_ir_sample.jsonl"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text("\n".join(lines), encoding="utf-8")

    axioms = load_axioms_from_ir(tmp)
    print("Axioms (from first 500 IR lines):", len(axioms))
    theorems = get_theorems(axioms, include_meaning_derivations=True)
    print("Theorems:", len(theorems))
    consistent = is_consistent(axioms)
    print("Consistent:", consistent)
    if not consistent:
        pairs = conflicting_pairs(axioms)
        print("Conflicting pairs:", len(pairs))
        for i, (n, m) in enumerate(pairs[:5]):
            s1 = decode_statement(n)
            s2 = decode_statement(m)
            t1 = (getattr(s1, "text", "") or "")[:50]
            t2 = (getattr(s2, "text", "") or "")[:50]
            print(f"  {i+1}. \"{t1}...\" vs \"{t2}...\"")
    else:
        print("No conflicting pairs.")

if __name__ == "__main__":
    main()
