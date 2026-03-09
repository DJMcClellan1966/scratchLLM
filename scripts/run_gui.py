#!/usr/bin/env python3
"""Simple GUI for formal-only Q&A (truth base + IR). Query, paths, options; Run and Check consistency."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    import tkinter as tk
    from tkinter import ttk, filedialog, scrolledtext, messagebox

    def browse_truth_base() -> None:
        p = filedialog.askopenfilename(
            title="Select truth base JSONL",
            filetypes=[("JSONL", "*.jsonl"), ("All", "*")],
        )
        if p:
            truth_base_var.set(p)

    def browse_ir() -> None:
        p = filedialog.askopenfilename(
            title="Select IR JSONL",
            filetypes=[("JSONL", "*.jsonl"), ("All", "*")],
        )
        if p:
            ir_var.set(p)

    def run_query() -> None:
        query = query_var.get().strip()
        if not query:
            messagebox.showinfo("Query", "Enter a query.")
            return
        tb = truth_base_var.get().strip() or None
        ir = ir_var.get().strip() or None
        if not tb and not ir:
            messagebox.showwarning("Paths", "Set at least one of Truth base or IR path.")
            return
        if tb and not Path(tb).exists():
            messagebox.showerror("Path", f"Truth base not found: {tb}")
            return
        if ir and not Path(ir).exists():
            messagebox.showerror("Path", f"IR file not found: {ir}")
            return
        try:
            from base import respond_formal_only
            try:
                top_k = int(top_k_var.get())
            except (ValueError, tk.TclError):
                top_k = 5
            result = respond_formal_only(
                query,
                truth_base_path=tb or None,
                ir_path=ir or None,
                top_k=max(1, min(50, top_k)),
                max_tier=max(0, min(6, max_tier_var.get())),
                resolve=not no_resolve_var.get(),
            )
            text = result[0] or "(no matching statements)"
            ids = result[1]
            statements = result[2] if len(result) > 2 else []
            out_lines = [text]
            if show_tiers_var.get() and statements:
                out_lines.append("")
                for s in statements:
                    tier = getattr(s, "tier", "")
                    t = (getattr(s, "text", "") or "")[:200]
                    out_lines.append(f"[Tier {tier}] {t}" + ("..." if len((getattr(s, "text", "") or "")) > 200 else ""))
            if show_ids_var.get() and ids:
                out_lines.append("")
                out_lines.append("Gödel IDs: " + ", ".join(str(n) for n in ids))
            response_text.delete("1.0", tk.END)
            response_text.insert(tk.END, "\n".join(out_lines))
        except Exception as e:
            response_text.delete("1.0", tk.END)
            response_text.insert(tk.END, f"Error: {e}")
            response_text.see(tk.END)

    def check_consistency() -> None:
        tb = truth_base_var.get().strip() or None
        ir = ir_var.get().strip() or None
        if not tb and not ir:
            messagebox.showwarning("Paths", "Set at least one of Truth base or IR path.")
            return
        if tb and not Path(tb).exists():
            messagebox.showerror("Path", f"Truth base not found: {tb}")
            return
        if ir and not Path(ir).exists():
            messagebox.showerror("Path", f"IR file not found: {ir}")
            return
        try:
            from base import check_consistency_of_paths
            consistent, pairs = check_consistency_of_paths(
                truth_base_path=tb,
                ir_path=ir,
            )
            if consistent:
                messagebox.showinfo("Consistency", "Consistent: yes.")
            else:
                messagebox.showwarning(
                    "Consistency",
                    f"Consistent: no.\nConflicting pairs: {len(pairs)}.",
                )
        except Exception as e:
            messagebox.showerror("Consistency", str(e))

    root = tk.Tk()
    root.title("scratchLLM – Formal Q&A (language + Gödel)")
    root.minsize(500, 400)

    f = ttk.Frame(root, padding=10)
    f.pack(fill=tk.BOTH, expand=True)

    # Load verticals and build dropdown
    from base.vertical import load_verticals_config, get_vertical, resolve_paths
    verticals_config = load_verticals_config()
    vertical_ids = list(verticals_config.keys())
    vertical_labels = [verticals_config[v].get("label", v) for v in vertical_ids]

    def on_vertical_change(*_args) -> None:
        sel = vertical_var.get()
        if sel not in vertical_labels or not vertical_ids:
            return
        vid = vertical_ids[vertical_labels.index(sel)]
        vertical = get_vertical(verticals_config, vid)
        if vertical:
            tb_path, ir_path, mt = resolve_paths(vertical, base_dir=ROOT)
            truth_base_var.set(str(tb_path) if tb_path else "")
            ir_var.set(str(ir_path) if ir_path else "")
            max_tier_var.set(mt)

    ttk.Label(f, text="Query:").grid(row=0, column=0, sticky=tk.W)
    query_var = tk.StringVar()
    query_entry = ttk.Entry(f, textvariable=query_var, width=50)
    query_entry.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=(5, 0), pady=2)

    ttk.Label(f, text="Vertical:").grid(row=1, column=0, sticky=tk.W)
    vertical_var = tk.StringVar(value=vertical_labels[0] if vertical_labels else "General")
    vertical_combo = ttk.Combobox(f, textvariable=vertical_var, values=vertical_labels, state="readonly", width=42)
    vertical_combo.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=(5, 0), pady=2)
    vertical_var.trace_add("write", on_vertical_change)
    if vertical_labels:
        on_vertical_change()

    ttk.Label(f, text="Truth base:").grid(row=2, column=0, sticky=tk.W)
    truth_base_var = tk.StringVar()
    ttk.Entry(f, textvariable=truth_base_var, width=45).grid(row=2, column=1, sticky=tk.EW, padx=(5, 5), pady=2)
    ttk.Button(f, text="Browse…", command=browse_truth_base).grid(row=2, column=2, pady=2)

    ttk.Label(f, text="IR JSONL:").grid(row=3, column=0, sticky=tk.W)
    ir_var = tk.StringVar()
    ttk.Entry(f, textvariable=ir_var, width=45).grid(row=3, column=1, sticky=tk.EW, padx=(5, 5), pady=2)
    ttk.Button(f, text="Browse…", command=browse_ir).grid(row=3, column=2, pady=2)

    max_tier_var = tk.IntVar(value=2)

    opts = ttk.Frame(f)
    opts.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=6)
    top_k_var = tk.IntVar(value=5)
    ttk.Label(opts, text="Top-k:").pack(side=tk.LEFT)
    tk.Spinbox(opts, from_=1, to=50, width=4, textvariable=top_k_var).pack(side=tk.LEFT, padx=(5, 15))
    ttk.Label(opts, text="Max tier:").pack(side=tk.LEFT, padx=(15, 0))
    tk.Spinbox(opts, from_=0, to=6, width=2, textvariable=max_tier_var).pack(side=tk.LEFT, padx=(5, 15))
    show_ids_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(opts, text="Show Gödel IDs", variable=show_ids_var).pack(side=tk.LEFT, padx=5)
    show_tiers_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(opts, text="Show tiers", variable=show_tiers_var).pack(side=tk.LEFT, padx=5)
    no_resolve_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(opts, text="Skip conflict resolution", variable=no_resolve_var).pack(side=tk.LEFT, padx=5)

    btn_frame = ttk.Frame(f)
    btn_frame.grid(row=5, column=0, columnspan=3, pady=6)
    ttk.Button(btn_frame, text="Run", command=run_query).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Check consistency", command=check_consistency).pack(side=tk.LEFT, padx=2)

    ttk.Label(f, text="Response:").grid(row=6, column=0, sticky=tk.NW, pady=(10, 2))
    response_text = scrolledtext.ScrolledText(f, wrap=tk.WORD, width=60, height=15)
    response_text.grid(row=7, column=0, columnspan=3, sticky=tk.NSEW, padx=(5, 0), pady=2)

    f.columnconfigure(1, weight=1)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    query_entry.focus()
    root.mainloop()


if __name__ == "__main__":
    main()
