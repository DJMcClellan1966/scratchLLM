"""Vertical presets: load config, resolve paths and max_tier for domain-specific defaults (medical, legal, general)."""
import json
from pathlib import Path
from typing import Any, Optional


def _default_config_path() -> Path:
    """Path to config/verticals.json relative to project root (base's parent)."""
    return Path(__file__).resolve().parent.parent / "config" / "verticals.json"


def load_verticals_config(path: Optional[str | Path] = None) -> dict[str, dict[str, Any]]:
    """
    Load verticals config from JSON. Returns dict id -> vertical config.
    If path is None, use config/verticals.json in project root.
    """
    p = Path(path) if path else _default_config_path()
    if not p.exists():
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, dict) and v.get("id")}


def get_vertical(verticals_config: dict[str, dict[str, Any]], vertical_id: str) -> Optional[dict[str, Any]]:
    """Return vertical config for vertical_id, or None if not found."""
    return verticals_config.get(vertical_id)


def resolve_vertical(
    vertical_id: str,
    truth_base_override: Optional[str | Path] = None,
    ir_override: Optional[str | Path] = None,
    max_tier_override: Optional[int] = None,
    base_dir: Optional[Path] = None,
) -> tuple[Optional[Path], Optional[Path], int, bool]:
    """
    Load config, get vertical, resolve paths. Returns (truth_base_path, ir_path, max_tier, vertical_found).
    When vertical_id is not in config, returns overrides (or None) and vertical_found=False.
    """
    config = load_verticals_config()
    vertical = get_vertical(config, vertical_id)
    if not vertical:
        tb = Path(truth_base_override) if truth_base_override else None
        ir = Path(ir_override) if ir_override else None
        mt = max_tier_override if max_tier_override is not None else 2
        return (tb, ir, mt, False)
    tb, ir, mt = resolve_paths(
        vertical, truth_base_override, ir_override, max_tier_override, base_dir
    )
    return (tb, ir, mt, True)


def resolve_paths(
    vertical: dict[str, Any],
    truth_base_override: Optional[str | Path] = None,
    ir_override: Optional[str | Path] = None,
    max_tier_override: Optional[int] = None,
    base_dir: Optional[Path] = None,
) -> tuple[Optional[Path], Optional[Path], int]:
    """
    Resolve truth_base_path, ir_path, max_tier from vertical defaults and overrides.
    Explicit overrides take precedence. Paths from config are resolved relative to base_dir (default: project root).
    Returns (truth_base_path, ir_path, max_tier).
    """
    base = base_dir or Path(__file__).resolve().parent.parent
    tb = truth_base_override
    if tb is not None:
        tb = Path(tb)
    else:
        raw = vertical.get("default_truth_base")
        if raw:
            tb = base / raw if not Path(str(raw)).is_absolute() else Path(raw)
    ir = ir_override
    if ir is not None:
        ir = Path(ir)
    else:
        raw = vertical.get("default_ir")
        if raw:
            ir = base / raw if not Path(str(raw)).is_absolute() else Path(raw)
    max_tier = max_tier_override if max_tier_override is not None else int(vertical.get("default_max_tier", 2))
    return (tb, ir, max_tier)
