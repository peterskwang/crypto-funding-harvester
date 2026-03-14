"""Utility helpers for reading and writing the strategy state."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def _default_state() -> Dict[str, Any]:
    return {
        "equity": 0.0,
        "realized_pnl": 0.0,
        "open_positions": {},
        "funding_history": [],
    }


def load_state(filepath: str) -> Dict[str, Any]:
    """Loads the strategy state from a JSON file."""
    path = Path(filepath)
    if not path.exists():
        state = _default_state()
        save_state(filepath, state)
        return state

    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)

    # Ensure essential keys exist
    default = _default_state()
    for key, value in default.items():
        data.setdefault(key, value if not isinstance(value, dict) else value.copy())
    return data


def save_state(filepath: str, state: Dict[str, Any]):
    """Saves the strategy state to a JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(state, fp, indent=2, sort_keys=False)
