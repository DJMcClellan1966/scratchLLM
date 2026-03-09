"""Tests for generate_compliance_report script."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_compliance_report_produces_expected_keys():
    """generate_compliance_report with a truth base produces report with expected keys."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write('{"text": "A is B.", "tier": 0, "source": "curated"}\n')
        tb_path = f.name
    out_path = Path(tempfile.gettempdir()) / "scratchllm_compliance_report_test.json"
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "generate_compliance_report.py"),
                "--truth-base", tb_path,
                "--output", str(out_path),
                "--format", "json",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert out_path.exists()
        report = json.loads(out_path.read_text(encoding="utf-8"))
        assert "generated_at" in report
        assert "consistency" in report
        assert report["consistency"]["consistent"] is True
        assert "axiom_count" in report
        assert report["axiom_count"] >= 1
        assert "tier_breakdown" in report
    finally:
        Path(tb_path).unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)
