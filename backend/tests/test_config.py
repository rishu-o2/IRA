from __future__ import annotations

from ira.config import gemini_api_key


def test_gemini_api_key_loads_from_env_file() -> None:
    key = gemini_api_key()

    assert key
