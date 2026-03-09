#!/usr/bin/env python3
"""Simple GUI for formal-only Q&A: create helper from intent (primary) or use prebuilt vertical (secondary)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

USER_HELPERS_DIR = ROOT / "corpus" / "user_helpers"


def main() -> None:
    import tkinter as tk
    from tkinter import ttk, filedialog, scrolledtext, messagebox

    def refresh_my_helpers() -> list[dict]:
        try:
            from base.intent import list_user_helpers
            return list_user_helpers(USER_HELPERS_DIR)
        except Exception:
            return []

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
            include_audit = include_audit_var.get()
            sel = helper_var.get()
            vertical_id = None
            if sel in prebuilt_labels and vertical_ids:
                vertical_id = vertical_ids[prebuilt_labels.index(sel)]
            result = respond_formal_only(
                query,
                truth_base_path=tb or None,
                ir_path=ir or None,
                top_k=max(1, min(50, top_k)),
                max_tier=max(0, min(6, max_tier_var.get())),
                resolve=not no_resolve_var.get(),
                include_audit=include_audit,
                run_consistency_check=include_audit,
                vertical_id=vertical_id,
            )
            text = result[0] or "(no matching statements)"
            ids = result[1]
            statements = result[2] if len(result) > 2 else []
            audit = result[3] if len(result) > 3 else None
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
            if include_audit and audit:
                out_lines.append("")
                out_lines.append("Audit: {} citations, consistency: {}".format(
                    len(ids),
                    "yes" if audit.get("consistent") is True else ("no" if audit.get("consistent") is False else "not checked"),
                ))
                audit_path = ROOT / "last_audit.json"
                try:
                    import json
                    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass
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

    # Load verticals (prebuilt) and my helpers
    from base.vertical import load_verticals_config, resolve_vertical
    verticals_config = load_verticals_config()
    vertical_ids = list(verticals_config.keys())
    prebuilt_labels = [verticals_config[v].get("label", v) for v in vertical_ids]

    my_helpers: list[dict] = []  # [{helper_id, truth_base_path, intent}, ...]
    helper_option_values: list[str] = []  # labels for dropdown: "My: X", "--- Prebuilt ---", "General", ...

    def build_helper_options() -> list[str]:
        nonlocal my_helpers
        my_helpers = refresh_my_helpers()
        opts = [f"My: {h['helper_id']}" for h in my_helpers]
        if prebuilt_labels:
            opts.append("--- Prebuilt ---")
            opts.extend(prebuilt_labels)
        return opts if opts else ["(No helpers — create one below)"]

    def on_helper_change(*_args) -> None:
        sel = helper_var.get()
        if not sel or sel == "(No helpers — create one below)":
            return
        if sel == "--- Prebuilt ---":
            return
        # My helper
        for h in my_helpers:
            if f"My: {h['helper_id']}" == sel:
                truth_base_var.set(h["truth_base_path"])
                ir_var.set("")
                max_tier_var.set(2)
                return
        # Prebuilt
        if sel in prebuilt_labels and vertical_ids:
            vid = vertical_ids[prebuilt_labels.index(sel)]
            tb_path, ir_path, mt, _ = resolve_vertical(vid, base_dir=ROOT)
            truth_base_var.set(str(tb_path) if tb_path else "")
            ir_var.set(str(ir_path) if ir_path else "")
            max_tier_var.set(mt)

    def create_helper() -> None:
        intent = intent_var.get().strip()
        if not intent:
            messagebox.showinfo("Create helper", "Enter what you want help with (e.g. 'I want to junk journal').")
            return
        try:
            from base.intent import create_helper_from_intent
            helper_id, truth_base_path, count = create_helper_from_intent(
                intent, out_dir=USER_HELPERS_DIR
            )
            helper_option_values[:] = build_helper_options()
            helper_combo["values"] = helper_option_values
            helper_var.set(f"My: {helper_id}")
            truth_base_var.set(str(truth_base_path))
            ir_var.set("")
            max_tier_var.set(2)
            messagebox.showinfo("Create helper", f"Created helper '{helper_id}' with {count} statements.")
        except ValueError as e:
            messagebox.showerror("Create helper", str(e))

    helper_option_values[:] = build_helper_options()
    default_helper = ""
    if my_helpers:
        default_helper = f"My: {my_helpers[0]['helper_id']}"
    elif prebuilt_labels:
        default_helper = prebuilt_labels[0]
    elif helper_option_values:
        default_helper = helper_option_values[0]

    ttk.Label(f, text="What do you want help with?").grid(row=0, column=0, sticky=tk.W)
    intent_var = tk.StringVar()
    ttk.Entry(f, textvariable=intent_var, width=50).grid(row=0, column=1, sticky=tk.EW, padx=(5, 5), pady=2)
    ttk.Button(f, text="Create helper", command=create_helper).grid(row=0, column=2, pady=2)

    ttk.Label(f, text="Query:").grid(row=1, column=0, sticky=tk.W)
    query_var = tk.StringVar()
    query_entry = ttk.Entry(f, textvariable=query_var, width=50)
    query_entry.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=(5, 0), pady=2)

    ttk.Label(f, text="Helper:").grid(row=2, column=0, sticky=tk.W)
    helper_var = tk.StringVar(value=default_helper)
    helper_combo = ttk.Combobox(f, textvariable=helper_var, values=helper_option_values, state="readonly", width=42)
    helper_combo.grid(row=2, column=1, columnspan=2, sticky=tk.EW, padx=(5, 0), pady=2)
    helper_var.trace_add("write", on_helper_change)
    if default_helper and default_helper != "(No helpers — create one below)":
        on_helper_change()

    ttk.Label(f, text="Truth base:").grid(row=3, column=0, sticky=tk.W)
    truth_base_var = tk.StringVar()
    ttk.Entry(f, textvariable=truth_base_var, width=45).grid(row=3, column=1, sticky=tk.EW, padx=(5, 5), pady=2)
    ttk.Button(f, text="Browse…", command=browse_truth_base).grid(row=3, column=2, pady=2)

    ttk.Label(f, text="IR JSONL:").grid(row=4, column=0, sticky=tk.W)
    ir_var = tk.StringVar()
    ttk.Entry(f, textvariable=ir_var, width=45).grid(row=4, column=1, sticky=tk.EW, padx=(5, 5), pady=2)
    ttk.Button(f, text="Browse…", command=browse_ir).grid(row=4, column=2, pady=2)

    max_tier_var = tk.IntVar(value=2)

    opts = ttk.Frame(f)
    opts.grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=6)
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
    include_audit_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(opts, text="Include audit (citations + consistency)", variable=include_audit_var).pack(side=tk.LEFT, padx=5)

    btn_frame = ttk.Frame(f)
    btn_frame.grid(row=6, column=0, columnspan=3, pady=6)
    ttk.Button(btn_frame, text="Run", command=run_query).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Check consistency", command=check_consistency).pack(side=tk.LEFT, padx=2)

    ttk.Label(f, text="Response:").grid(row=7, column=0, sticky=tk.NW, pady=(10, 2))
    response_text = scrolledtext.ScrolledText(f, wrap=tk.WORD, width=60, height=15)
    response_text.grid(row=8, column=0, columnspan=3, sticky=tk.NSEW, padx=(5, 0), pady=2)

    f.columnconfigure(1, weight=1)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    query_entry.focus()
    root.mainloop()


if __name__ == "__main__":
    main()
