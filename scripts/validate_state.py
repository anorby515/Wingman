#!/usr/bin/env python3
"""
Validate Wingman Data Files
============================
Validates concert_state.json (and optionally other data files) against
the Pydantic models defined in backend/models.py.

Run before committing data to ensure schema compliance:
    python scripts/validate_state.py

Exit code 0 = valid, 1 = validation errors found.
"""

import json
import sys
from pathlib import Path

# Add repo root to path so we can import backend.models
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from backend.models import ConcertState, WingmanConfig, Summary


def validate_file(path: Path, model_class, label: str) -> bool:
    """Validate a JSON file against a Pydantic model. Returns True if valid."""
    if not path.exists():
        print(f"  SKIP  {label}: {path.name} not found")
        return True  # Not an error — file may not exist yet

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"  FAIL  {label}: invalid JSON — {e}")
        return False

    try:
        model_class(**data)
        print(f"  OK    {label}: {path.name} is valid")
        return True
    except Exception as e:
        print(f"  FAIL  {label}: {e}")
        return False


def main():
    print("Validating Wingman data files...\n")

    results = []

    # concert_state.json
    results.append(validate_file(
        REPO / "concert_state.json",
        ConcertState,
        "Concert State",
    ))

    # wingman_config.json
    results.append(validate_file(
        REPO / "wingman_config.json",
        WingmanConfig,
        "Wingman Config",
    ))

    # docs/summary.json
    results.append(validate_file(
        REPO / "docs" / "summary.json",
        Summary,
        "Summary",
    ))

    print()
    if all(results):
        print("All files valid.")
        sys.exit(0)
    else:
        print("Validation errors found. Fix before committing.")
        sys.exit(1)


if __name__ == "__main__":
    main()
