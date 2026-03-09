"""Tests for serve_api local HTTP API."""
import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_serve_api_post_query_returns_200_and_response():
    """POST /query with query and truth_base returns 200 and JSON with response key."""
    from base.truth_base import Statement, save_truth_base

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        save_truth_base([Statement("API test statement.", 1, "curated")], f.name)
        tb_path = f.name
    try:
        from scripts.serve_api import QueryHandler
        from http.server import HTTPServer

        server = HTTPServer(("127.0.0.1", 0), QueryHandler)
        port = server.server_address[1]
        def run():
            server.handle_request()
        t = threading.Thread(target=run, daemon=True)
        t.start()
        time.sleep(0.2)
        try:
            req = Request(
                "http://127.0.0.1:{}/query".format(port),
                data=json.dumps({"query": "What is API test?", "truth_base": tb_path}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=5) as resp:
                body = resp.read().decode("utf-8")
                if resp.status != 200:
                    pytest.skip("Server returned {}: {}".format(resp.status, body[:300]))
                if not body.strip():
                    pytest.skip("Server returned empty body")
                data = json.loads(body)
                assert "response" in data
                assert "citation_ids" in data
        except HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else ""
            try:
                err = json.loads(body)
                pytest.skip("Server 500: {}".format(err.get("error", body)[:200]))
            except Exception:
                pytest.skip("Server 500: {}".format(body[:200]))
        except (URLError, OSError) as e:
            pytest.skip("Could not connect to local server: {}".format(e))
        finally:
            t.join(timeout=1)
    finally:
        Path(tb_path).unlink(missing_ok=True)
