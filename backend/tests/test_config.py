from __future__ import annotations

from ira.config import google_api_key


def test_google_api_key_loads_from_env_file() -> None:
    key = google_api_key()

    assert key is not None
    assert key.startswith("AIza")
