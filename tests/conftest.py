"""
Shared fixtures for Wingman backend tests.

Provides a FastAPI TestClient that operates against a temporary config directory
so tests never read/write the real wingman_config.json or other data files.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Minimal valid config for tests
MINIMAL_CONFIG = {
    "center_city": "Des Moines, IA",
    "radius_miles": 200,
    "cities_in_range": [],
    "states_in_range": [],
    "artists": {},
    "venues": {},
    "festivals": {},
}


@pytest.fixture()
def tmp_config(tmp_path: Path):
    """Write a minimal wingman_config.json into a temp dir and return its path."""
    config_file = tmp_path / "wingman_config.json"
    config_file.write_text(json.dumps(MINIMAL_CONFIG, indent=2))
    return config_file


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    """Return a TestClient wired to temp files so tests are fully isolated."""
    import backend.main as main_mod

    config_file = tmp_path / "wingman_config.json"
    config_file.write_text(json.dumps(MINIMAL_CONFIG, indent=2))

    tracked_file = tmp_path / "tracked.json"
    flagged_file = tmp_path / "flagged_items.json"
    geocode_file = tmp_path / "geocode_cache.json"

    monkeypatch.setattr(main_mod, "CONFIG_FILE", config_file)
    monkeypatch.setattr(main_mod, "TRACKED_FILE", tracked_file)
    monkeypatch.setattr(main_mod, "FLAGGED_FILE", flagged_file)
    monkeypatch.setattr(main_mod, "GEOCODE_FILE", geocode_file)

    # Stub out geocoding so tests never hit the network
    monkeypatch.setattr(main_mod, "_geocode", lambda loc: None)

    return TestClient(main_mod.app)
