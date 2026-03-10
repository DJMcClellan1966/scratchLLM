#!/usr/bin/env python3
"""
Intent-first GUI: minimal and adaptive.
- Welcome: one question, one input, Get started. No technical details.
- Working: once the user states their need, the UI aligns to it — friendly title and placeholder.
- Settings: advanced options (paths, consistency, audit) hidden for power users.
"""
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

    def get_template_theme(intent: str) -> dict:
        """Return theme dict: label, placeholder, welcome_headline, accent_color, default_actions, default_action_queries."""
        try:
            from base.intent import load_intent_templates, get_template_for_intent
            templates = load_intent_templates()
            tid = get_template_for_intent(intent, templates)
            if tid and tid in templates:
                t = templates[tid]
                return {
                    "label": t.get("label", "Align"),
                    "placeholder": t.get("placeholder", "Ask anything…"),
                    "welcome_headline": t.get("welcome_headline"),
                    "accent_color": t.get("accent_color"),
                    "default_actions": t.get("default_actions") or [],
                    "default_action_queries": t.get("default_action_queries") or [],
                }
        except Exception:
            pass
        short = (intent.strip()[:40] + "…") if len(intent.strip()) > 40 else intent.strip()
        return {
            "label": short or "Align",
            "placeholder": "Ask anything…",
            "welcome_headline": None,
            "accent_color": None,
            "default_actions": [],
            "default_action_queries": [],
        }

    root = tk.Tk()
    root.title("Align")
    root.minsize(480, 420)
    root.geometry("520x480")

    # State: current helper = None or dict with truth_base_path, ir_path, intent, display_label, placeholder, is_prebuilt, vertical_id?
    current_helper: dict | None = None
    truth_base_var = tk.StringVar()
    ir_var = tk.StringVar()
    max_tier_var = tk.IntVar(value=2)
    experience_level_var = tk.StringVar(value="beginner")
    needs_vocabulary_var = tk.BooleanVar(value=False)
    top_k_var = tk.IntVar(value=5)
    include_audit_var = tk.BooleanVar(value=False)
    vertical_ids: list[str] = []
    prebuilt_labels: list[str] = []

    from base.vertical import load_verticals_config, resolve_vertical
    verticals_config = load_verticals_config()
    # Sample dropdown: only Bible & daily reading; full verticals_config still used for resolve_vertical
    sample_vertical_ids = [v for v in verticals_config.keys() if v == "bible_daily"]
    prebuilt_labels = [verticals_config[v].get("label", v) for v in sample_vertical_ids]

    my_helpers: list[dict] = []
    last_conversation: dict[str, str] = {"query": "", "response": ""}

    def run_query() -> None:
        q = query_var.get().strip()
        if not q or q == getattr(query_entry, "placeholder", ""):
            return
        tb = truth_base_var.get().strip() or None
        ir = ir_var.get().strip() or None
        if not tb and not ir:
            messagebox.showinfo("Ask", "No helper is active. Create or choose one first.")
            return
        if tb and not Path(tb).exists():
            messagebox.showerror("Error", "Helper data not found. Try switching or creating a new helper.")
            return
        try:
            from base import respond_formal_only
            sel = current_helper
            vertical_id = sel.get("vertical_id") if sel and sel.get("is_prebuilt") else None
            result = respond_formal_only(
                q,
                truth_base_path=tb or None,
                ir_path=ir or None,
                top_k=max(1, min(50, top_k_var.get())),
                max_tier=max(0, min(6, max_tier_var.get())),
                resolve=True,
                include_audit=include_audit_var.get(),
                run_consistency_check=include_audit_var.get(),
                vertical_id=vertical_id,
            )
            text = result[0] or "I don’t have a clear answer for that yet. Try rephrasing or adding more in Align."
            response_text.delete("1.0", tk.END)
            response_text.insert(tk.END, text)
            last_conversation["query"] = q
            last_conversation["response"] = text
            if include_audit_var.get() and result[3]:
                audit = result[3]
                try:
                    import json
                    (ROOT / "last_audit.json").write_text(
                        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                except Exception:
                    pass
        except Exception as e:
            response_text.delete("1.0", tk.END)
            response_text.insert(tk.END, f"Something went wrong: {e}")

    def set_helper(h: dict) -> None:
        nonlocal current_helper
        current_helper = h
        truth_base_var.set(h.get("truth_base_path", ""))
        ir_var.set(h.get("ir_path", ""))
        max_tier_var.set(h.get("max_tier", 2))
        header_label.config(text=h.get("display_label", "Align"))
        try:
            header_label.config(foreground=h.get("accent_color") or "black")
        except tk.TclError:
            pass
        if welcome_headline_var is not None:
            welcome_headline_var.set(h.get("welcome_headline") or "")
        ph = h.get("placeholder", "Ask anything…")
        query_entry.delete(0, tk.END)
        query_entry.insert(0, "")
        query_entry.placeholder = ph
        _set_placeholder(query_entry, ph)
        root.title(f"Align — {h.get('display_label', 'Helper')}")
        actions = h.get("default_actions") or []
        queries = h.get("default_action_queries") or []
        for w in actions_frame.winfo_children():
            w.destroy()
        for i, label in enumerate(actions):
            q = queries[i] if i < len(queries) else label
            btn = ttk.Button(actions_frame, text=label, command=lambda qq=q: _run_preset_query(qq))
            btn.pack(side=tk.LEFT, padx=(0, 6))
        # Show personalizer buttons only for user helpers (writable truth base)
        if personalizer_frame.winfo_ismapped():
            personalizer_frame.pack_forget()
        if h and not h.get("is_prebuilt") and h.get("truth_base_path"):
            personalizer_frame.pack(anchor=tk.W, pady=(0, 8))

    def _run_preset_query(preset_query: str) -> None:
        query_var.set(preset_query)
        _clear_placeholder(query_entry)
        query_entry.delete(0, tk.END)
        query_entry.insert(0, preset_query)
        run_query()

    def _set_placeholder(entry: tk.Entry, text: str) -> None:
        try:
            entry.placeholder = text
            if not entry.get().strip():
                entry.delete(0, tk.END)
                entry.insert(0, text)
                try:
                    entry.config(fg="gray")
                except tk.TclError:
                    pass
        except Exception:
            pass

    def _clear_placeholder(entry: tk.Entry) -> None:
        try:
            if getattr(entry, "placeholder", None) and entry.get().strip() == entry.placeholder:
                entry.delete(0, tk.END)
                try:
                    entry.config(fg="black")
                except tk.TclError:
                    pass
        except Exception:
            pass

    def _restore_placeholder(entry: tk.Entry) -> None:
        try:
            if getattr(entry, "placeholder", None) and not entry.get().strip():
                entry.delete(0, tk.END)
                entry.insert(0, entry.placeholder)
                try:
                    entry.config(fg="gray")
                except tk.TclError:
                    pass
        except Exception:
            pass

    def remember_this_click() -> None:
        tb = truth_base_var.get().strip() or None
        if not tb or not Path(tb).exists():
            messagebox.showinfo("Remember this", "No helper data to add to. Switch to a user helper first.")
            return
        try:
            from base.learning import append_to_truth_base, statements_from_user_note
            from base.truth_base import Statement
            new_stmts = []
            if last_conversation.get("query", "").strip():
                new_stmts.extend(statements_from_user_note(last_conversation["query"].strip(), category="user_note"))
            if last_conversation.get("response", "").strip():
                new_stmts.append(Statement(
                    text="Assistant said: " + last_conversation["response"].strip()[:500],
                    tier=2, source="assistant", category="memory",
                ))
            if not new_stmts:
                messagebox.showinfo("Remember this", "Ask something first, then click Remember this to save the exchange.")
                return
            append_to_truth_base(tb, new_stmts)
            messagebox.showinfo("Remember this", "Saved to your helper.")
        except Exception as e:
            messagebox.showerror("Remember this", str(e))

    def record_outcome_click() -> None:
        tb = truth_base_var.get().strip() or None
        if not tb or not Path(tb).exists():
            messagebox.showinfo("Record outcome", "No helper data to add to. Switch to a user helper first.")
            return
        win = tk.Toplevel(root)
        win.title("Record outcome")
        win.geometry("420x220")
        ttk.Label(win, text="Experiment description").pack(anchor=tk.W, padx=10, pady=(10, 2))
        desc_var = tk.StringVar()
        ttk.Entry(win, textvariable=desc_var, width=50).pack(fill=tk.X, padx=10, pady=(0, 8))
        ttk.Label(win, text="Result").pack(anchor=tk.W, padx=10, pady=(0, 2))
        result_var = tk.StringVar(value="success")
        result_combo = ttk.Combobox(win, textvariable=result_var, values=["success", "failure", "skipped"], state="readonly", width=20)
        result_combo.pack(anchor=tk.W, padx=10, pady=(0, 8))
        ttk.Label(win, text="Notes (optional)").pack(anchor=tk.W, padx=10, pady=(0, 2))
        notes_var = tk.StringVar()
        ttk.Entry(win, textvariable=notes_var, width=50).pack(fill=tk.X, padx=10, pady=(0, 8))

        def submit_outcome() -> None:
            desc = desc_var.get().strip()
            if not desc:
                messagebox.showinfo("Record outcome", "Enter an experiment description.", parent=win)
                return
            try:
                from base.learning import append_to_truth_base, statements_from_outcome
                stmts = statements_from_outcome(desc, result_var.get().strip(), notes_var.get().strip())
                append_to_truth_base(tb, stmts)
                win.destroy()
                messagebox.showinfo("Record outcome", "Outcome saved to your helper.")
            except Exception as e:
                messagebox.showerror("Record outcome", str(e), parent=win)

        btn_f = ttk.Frame(win)
        btn_f.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_f, text="Submit", command=submit_outcome).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_f, text="Cancel", command=win.destroy).pack(side=tk.LEFT)

    def suggest_experiment_click() -> None:
        suggest_query = "Suggest 1–2 experiments or next steps based on my goals and what I've tried."
        query_var.set(suggest_query)
        _clear_placeholder(query_entry)
        query_entry.delete(0, tk.END)
        query_entry.insert(0, suggest_query)
        run_query()

    def show_working_view() -> None:
        welcome_frame.pack_forget()
        working_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

    def show_welcome_view() -> None:
        working_frame.pack_forget()
        welcome_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)
        root.title("Align")

    def show_onboarding_step1() -> None:
        onboarding_step2_frame.pack_forget()
        onboarding_step1_frame.pack(fill=tk.BOTH, expand=True)

    def show_onboarding_step2() -> None:
        intent = intent_var.get().strip()
        if not intent:
            messagebox.showinfo("Next", "Type what you want help with (e.g. I want to learn about birdwatching).")
            return
        try:
            from base.intent import check_guardrails
            allowed, _ = check_guardrails(intent)
            if not allowed:
                messagebox.showerror("Cannot continue", "That request cannot be supported. Please describe a different kind of help.")
                return
        except Exception:
            pass
        try:
            from base.intent import get_template_for_intent, load_intent_templates, get_onboarding_definitions
            templates = load_intent_templates()
            tid = get_template_for_intent(intent, templates)
            defs = get_onboarding_definitions(tid, base_dir=ROOT, max_definitions=3)
            if defs:
                parts = [f"{t} — {d}" if d else t for t, d in defs]
                onboarding_terms_var.set("We'll use terms like: " + "; ".join(parts))
            else:
                onboarding_terms_var.set("")
        except Exception:
            onboarding_terms_var.set("")
        onboarding_step1_frame.pack_forget()
        onboarding_step2_frame.pack(fill=tk.BOTH, expand=True)

    def create_and_enter_helper() -> None:
        intent = intent_var.get().strip()
        if not intent:
            messagebox.showinfo("Create my helper", "Type what you want help with — for example, \"I want to junk journal\" or \"I’m planning a hike\".")
            return
        try:
            from base.intent import create_helper_from_intent, get_template_for_intent, load_intent_templates
            experience_level = experience_level_var.get().strip() or None
            needs_vocabulary = needs_vocabulary_var.get()
            helper_id, tb_path, count = create_helper_from_intent(
                intent,
                out_dir=USER_HELPERS_DIR,
                blank_canvas=False,
                experience_level=experience_level,
                needs_vocabulary=needs_vocabulary,
            )
            templates = load_intent_templates()
            tid = get_template_for_intent(intent, templates)
            t = templates.get(tid, {}) if isinstance(templates, dict) else {}
            short_label = (intent.strip()[:36] + "…") if len(intent.strip()) > 36 else (intent.strip() or "Your helper")
            set_helper({
                "truth_base_path": str(tb_path),
                "ir_path": "",
                "intent": intent,
                "display_label": t.get("label", short_label) if t else short_label,
                "placeholder": t.get("placeholder", "Ask anything…") if t else "Ask anything…",
                "welcome_headline": t.get("welcome_headline", "") if t else "",
                "accent_color": t.get("accent_color") if t else None,
                "default_actions": t.get("default_actions") or [],
                "default_action_queries": t.get("default_action_queries") or [],
                "is_prebuilt": False,
                "helper_id": helper_id,
            })
            show_working_view()
            messagebox.showinfo("Ready", "Your helper is ready. It is tailored to your level and will learn with you.")
        except ValueError as e:
            messagebox.showerror("Can’t create helper", str(e))

    def use_prebuilt() -> None:
        sel = prebuilt_combo.get()
        if not sel or sel not in prebuilt_labels:
            return
        vid = sample_vertical_ids[prebuilt_labels.index(sel)]
        tb_path, ir_path, mt, _ = resolve_vertical(vid, base_dir=ROOT)
        label = verticals_config.get(vid, {}).get("label", sel)
        try:
            from base.intent import load_intent_templates
            templates = load_intent_templates()
            t = templates.get(vid, {}) if isinstance(templates, dict) else {}
            theme = {
                "label": t.get("label", label),
                "placeholder": t.get("placeholder", "Ask anything…"),
                "welcome_headline": t.get("welcome_headline"),
                "accent_color": t.get("accent_color"),
                "default_actions": t.get("default_actions") or [],
                "default_action_queries": t.get("default_action_queries") or [],
            }
        except Exception:
            theme = {"label": label, "placeholder": "Ask anything…", "welcome_headline": None, "accent_color": None, "default_actions": [], "default_action_queries": []}
        set_helper({
            "truth_base_path": str(tb_path) if tb_path else "",
            "ir_path": str(ir_path) if ir_path else "",
            "intent": "",
            "display_label": theme["label"],
            "placeholder": theme["placeholder"],
            "welcome_headline": theme.get("welcome_headline"),
            "accent_color": theme.get("accent_color"),
            "default_actions": theme.get("default_actions") or [],
            "default_action_queries": theme.get("default_action_queries") or [],
            "is_prebuilt": True,
            "vertical_id": vid,
            "max_tier": mt,
        })
        show_working_view()

    def open_my_helper() -> None:
        sel = my_helpers_combo.get()
        if not sel:
            return
        helpers_now = refresh_my_helpers()
        for h in helpers_now:
            if f"My: {h['helper_id']}" == sel:
                intent = h.get("intent", "")
                short_label = (intent[:36] + "…") if len(intent) > 36 else (intent or "Your helper")
                set_helper({
                    "truth_base_path": h["truth_base_path"],
                    "ir_path": "",
                    "intent": intent,
                    "display_label": short_label,
                    "placeholder": "Ask anything…",
                    "welcome_headline": "",
                    "accent_color": None,
                    "default_actions": [],
                    "default_action_queries": [],
                    "is_prebuilt": False,
                    "helper_id": h["helper_id"],
                })
                show_working_view()
                return

    def switch_helper_click() -> None:
        nonlocal my_helpers
        my_helpers = refresh_my_helpers()
        my_helpers_combo["values"] = [f"My: {x['helper_id']}" for x in my_helpers]
        if my_helpers:
            my_helpers_combo.set(f"My: {my_helpers[0]['helper_id']}")
            open_btn.config(state=tk.NORMAL)
        else:
            my_helpers_combo.set("")
            open_btn.config(state=tk.DISABLED)
        show_welcome_view()

    def open_settings() -> None:
        win = tk.Toplevel(root)
        win.title("Settings")
        win.geometry("420x280")
        ttk.Label(win, text="Paths and options (for advanced use)").pack(pady=(10, 6))
        pf = ttk.Frame(win, padding=10)
        pf.pack(fill=tk.BOTH, expand=True)
        ttk.Label(pf, text="Truth base:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(pf, textvariable=truth_base_var, width=44).grid(row=0, column=1, sticky=tk.EW, padx=4, pady=2)
        ttk.Button(pf, text="Browse…", command=_browse_tb).grid(row=0, column=2, pady=2)
        ttk.Label(pf, text="IR JSONL:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(pf, textvariable=ir_var, width=44).grid(row=1, column=1, sticky=tk.EW, padx=4, pady=2)
        ttk.Label(pf, text="Top-k:").grid(row=2, column=0, sticky=tk.W, pady=2)
        tk.Spinbox(pf, from_=1, to=50, width=6, textvariable=top_k_var).grid(row=2, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Checkbutton(pf, text="Include audit (save to last_audit.json)", variable=include_audit_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=4)
        def do_consistency() -> None:
            tb = truth_base_var.get().strip() or None
            ir = ir_var.get().strip() or None
            if not tb and not ir:
                messagebox.showwarning("Settings", "Set at least one path.")
                return
            try:
                from base import check_consistency_of_paths
                ok, pairs = check_consistency_of_paths(truth_base_path=tb, ir_path=ir)
                messagebox.showinfo("Consistency", "Consistent: yes." if ok else f"Consistent: no. {len(pairs)} conflict(s).")
            except Exception as e:
                messagebox.showerror("Consistency", str(e))
        ttk.Button(pf, text="Check consistency", command=do_consistency).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=4)
        pf.columnconfigure(1, weight=1)
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)

    # ----- Welcome frame -----
    welcome_frame = ttk.Frame(root)
    intent_var = tk.StringVar()
    onboarding_step1_frame = ttk.Frame(welcome_frame)
    ttk.Label(onboarding_step1_frame, text="What do you want help with?", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=(0, 8))
    ttk.Label(onboarding_step1_frame, text="For example: I want to learn about birdwatching, or an exercise program for me.", foreground="gray").pack(anchor=tk.W, pady=(0, 12))
    intent_entry = ttk.Entry(onboarding_step1_frame, textvariable=intent_var, width=52)
    intent_entry.pack(fill=tk.X, pady=(0, 12))
    ttk.Button(onboarding_step1_frame, text="Next", command=show_onboarding_step2).pack(anchor=tk.W, pady=(0, 24))

    onboarding_step2_frame = ttk.Frame(welcome_frame)
    onboarding_terms_var = tk.StringVar()
    ttk.Label(onboarding_step2_frame, text="Tell us a bit more", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=(0, 8))
    onboarding_terms_label = ttk.Label(onboarding_step2_frame, textvariable=onboarding_terms_var, foreground="gray", wraplength=440)
    onboarding_terms_label.pack(anchor=tk.W, pady=(0, 8))
    ttk.Label(onboarding_step2_frame, text="How would you describe your experience with this?", font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(0, 4))
    level_f = ttk.Frame(onboarding_step2_frame)
    level_f.pack(anchor=tk.W, pady=(0, 4))
    ttk.Radiobutton(level_f, text="Beginner", variable=experience_level_var, value="beginner").pack(side=tk.LEFT, padx=(0, 12))
    ttk.Radiobutton(level_f, text="Some experience", variable=experience_level_var, value="some_experience").pack(side=tk.LEFT, padx=(0, 12))
    ttk.Radiobutton(level_f, text="Advanced", variable=experience_level_var, value="advanced").pack(side=tk.LEFT)
    ttk.Label(onboarding_step2_frame, text="Do you want vocabulary and definitions included? (helpful for learning terms)", font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(12, 4))
    ttk.Checkbutton(onboarding_step2_frame, text="Yes, include definitions", variable=needs_vocabulary_var).pack(anchor=tk.W, pady=(0, 12))
    btn_f2 = ttk.Frame(onboarding_step2_frame)
    btn_f2.pack(anchor=tk.W, pady=(0, 8))
    ttk.Button(btn_f2, text="Create my helper", command=create_and_enter_helper).pack(side=tk.LEFT, padx=(0, 8))
    ttk.Button(btn_f2, text="Back", command=show_onboarding_step1).pack(side=tk.LEFT)

    onboarding_step1_frame.pack(fill=tk.BOTH, expand=True)

    ttk.Separator(welcome_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)
    ttk.Label(welcome_frame, text="Or explore a sample", font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(0, 6))
    prebuilt_combo = ttk.Combobox(welcome_frame, values=prebuilt_labels, state="readonly", width=36)
    prebuilt_combo.pack(side=tk.LEFT, pady=(0, 6))
    if prebuilt_labels:
        prebuilt_combo.set(prebuilt_labels[0])
    ttk.Button(welcome_frame, text="Use this", command=use_prebuilt).pack(side=tk.LEFT, padx=8, pady=(0, 6))

    ttk.Label(welcome_frame, text="Or open an existing helper", font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(16, 6))
    my_helpers_for_welcome = refresh_my_helpers()
    my_helpers_combo = ttk.Combobox(welcome_frame, values=[f"My: {x['helper_id']}" for x in my_helpers_for_welcome], state="readonly", width=36)
    my_helpers_combo.pack(side=tk.LEFT, pady=(0, 6))
    if my_helpers_for_welcome:
        my_helpers_combo.set(f"My: {my_helpers_for_welcome[0]['helper_id']}")
    open_btn = ttk.Button(welcome_frame, text="Open", command=open_my_helper)
    open_btn.pack(side=tk.LEFT, padx=8, pady=(0, 6))
    open_btn.config(state=tk.NORMAL if my_helpers_for_welcome else tk.DISABLED)

    # ----- Working frame -----
    working_frame = ttk.Frame(root)
    header_label = ttk.Label(working_frame, text="Align", font=("Segoe UI", 12, "bold"))
    header_label.pack(anchor=tk.W, pady=(0, 4))
    welcome_headline_var = tk.StringVar()
    welcome_headline_label = ttk.Label(working_frame, textvariable=welcome_headline_var, foreground="gray")
    welcome_headline_label.pack(anchor=tk.W, pady=(0, 8))

    query_var = tk.StringVar()
    query_entry = ttk.Entry(working_frame, textvariable=query_var, width=52)
    query_entry.pack(fill=tk.X, pady=(0, 6))
    query_entry.placeholder = "Ask anything…"
    query_entry.bind("<FocusIn>", lambda e: _clear_placeholder(query_entry))
    query_entry.bind("<FocusOut>", lambda e: _restore_placeholder(query_entry))
    query_entry.bind("<Return>", lambda e: run_query())

    ttk.Button(working_frame, text="Ask", command=run_query).pack(anchor=tk.W, pady=(0, 6))
    actions_frame = ttk.Frame(working_frame)
    actions_frame.pack(anchor=tk.W, pady=(0, 12))
    personalizer_frame = ttk.Frame(working_frame)
    ttk.Button(personalizer_frame, text="Remember this", command=remember_this_click).pack(side=tk.LEFT, padx=(0, 6))
    ttk.Button(personalizer_frame, text="Record outcome", command=record_outcome_click).pack(side=tk.LEFT, padx=(0, 6))
    ttk.Button(personalizer_frame, text="Suggest experiment", command=suggest_experiment_click).pack(side=tk.LEFT)

    ttk.Label(working_frame, text="Answer").pack(anchor=tk.W, pady=(8, 2))
    response_text = scrolledtext.ScrolledText(working_frame, wrap=tk.WORD, width=58, height=14, font=("Segoe UI", 10))
    response_text.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

    foot = ttk.Frame(working_frame)
    foot.pack(fill=tk.X)
    ttk.Button(foot, text="Switch helper", command=switch_helper_click).pack(side=tk.LEFT, padx=(0, 8))
    ttk.Button(foot, text="Settings", command=open_settings).pack(side=tk.LEFT)

    # Fix Settings browse: use a proper lambda that stores result
    def _browse_tb() -> None:
        p = filedialog.askopenfilename(title="Truth base", filetypes=[("JSONL", "*.jsonl"), ("All", "*")])
        if p:
            truth_base_var.set(p)

    # Startup: always show welcome (blank canvas first); user builds the app from their input
    welcome_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

    intent_entry.focus()
    root.mainloop()


if __name__ == "__main__":
    main()
