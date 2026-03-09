#!/usr/bin/env python3
"""Local HTTP API for formal-only Q&A. POST /query with JSON body; returns response + citations + audit. Bind to 127.0.0.1 only."""
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _audit_for_json(audit):
    """Return audit dict with citation_ids as strings (avoids JSON int digit limit)."""
    if audit is None:
        return None
    out = dict(audit)
    if "citation_ids" in out and out["citation_ids"]:
        out["citation_ids"] = [str(n) for n in out["citation_ids"]]
    return out


def _load_verticals():
    from base.vertical import load_verticals_config, get_vertical, resolve_paths
    return load_verticals_config(), get_vertical, resolve_paths


class QueryHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if urlparse(self.path).path != "/query":
            self.send_response(404)
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            data = json.loads(body) if body.strip() else {}
        except (json.JSONDecodeError, ValueError) as e:
            self._send_json(400, {"error": f"Invalid JSON: {e}"})
            return
        query = data.get("query") or data.get("prompt")
        if not query or not isinstance(query, str):
            self._send_json(400, {"error": "Missing or invalid 'query' (or 'prompt')"})
            return
        vertical_id = data.get("vertical")
        truth_base_override = data.get("truth_base")
        ir_override = data.get("ir")
        top_k = int(data.get("top_k", 5))
        max_tier = int(data.get("max_tier", 2))
        include_audit = bool(data.get("include_audit", True))

        truth_base_path = Path(truth_base_override) if truth_base_override else None
        ir_path = Path(ir_override) if ir_override else None
        if vertical_id:
            try:
                config, get_vertical, resolve_paths = _load_verticals()
                vertical = get_vertical(config, vertical_id)
                if vertical:
                    tb, ir, mt = resolve_paths(
                        vertical,
                        truth_base_override=truth_base_path,
                        ir_override=ir_path,
                        max_tier_override=max_tier,
                        base_dir=ROOT,
                    )
                    truth_base_path = tb
                    ir_path = ir
                    max_tier = mt
            except Exception:
                pass

        if not truth_base_path and not ir_path:
            self._send_json(400, {"error": "No truth base or IR path (set vertical or truth_base/ir in body)"})
            return

        try:
            from base import respond_formal_only
            response_text, citation_ids, resolved, audit = respond_formal_only(
                query,
                truth_base_path=truth_base_path,
                ir_path=ir_path,
                top_k=max(1, min(50, top_k)),
                max_tier=max(0, min(6, max_tier)),
                resolve=True,
                include_audit=include_audit,
                run_consistency_check=include_audit,
                vertical_id=vertical_id,
            )
            out = {
                "response": response_text or "(no matching statements)",
                "citation_ids": [str(n) for n in citation_ids],
                "tiers": [getattr(s, "tier", None) for s in resolved],
                "audit": _audit_for_json(audit),
            }
            self._send_json(200, out)
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _send_json(self, code: int, obj: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        safe = _strip_large_ints(obj)
        self.wfile.write(json.dumps(safe, ensure_ascii=False).encode("utf-8"))


def _strip_large_ints(obj, max_digits=4000):
    """Recursively convert ints with more than max_digits to str for JSON (avoids int string limit)."""
    if isinstance(obj, dict):
        return {k: _strip_large_ints(v, max_digits) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_large_ints(x, max_digits) for x in obj]
    if isinstance(obj, int):
        try:
            if obj.bit_length() > max_digits or (obj < 0 and (-obj).bit_length() > max_digits):
                return str(obj)
        except (AttributeError, OverflowError):
            return str(obj)
    return obj

    def log_message(self, format, *args):
        pass


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Local API: POST /query with JSON body. Binds to 127.0.0.1 only.")
    ap.add_argument("--port", type=int, default=8050, help="Port (default 8050)")
    ap.add_argument("--host", type=str, default="127.0.0.1", help="Host (default 127.0.0.1; use 127.0.0.1 for local only)")
    args = ap.parse_args()
    if args.host != "127.0.0.1" and args.host != "localhost":
        print("Warning: binding to non-local host. Use 127.0.0.1 for local-only.", file=sys.stderr)
    server = HTTPServer((args.host, args.port), QueryHandler)
    print(f"API listening on http://{args.host}:{args.port} — POST /query with JSON {{ \"query\", \"vertical\"?, \"truth_base\"?, \"ir\"?, \"top_k\"?, \"max_tier\"?, \"include_audit\"? }}", file=sys.stderr)
    server.serve_forever()


if __name__ == "__main__":
    main()
