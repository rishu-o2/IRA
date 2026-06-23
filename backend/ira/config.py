from __future__ import annotations

import os
from pathlib import Path


def load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"

    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        clean_line = line.strip()

        if not clean_line or clean_line.startswith("#") or "=" not in clean_line:
            continue

        key, value = clean_line.split("=", 1)
        clean_key = key.strip().lstrip("\ufeff")
        os.environ.setdefault(clean_key, value.strip().strip('"').strip("'"))


def google_api_key() -> str | None:
    load_env_file()
    return os.environ.get("GOOGLE_API_KEY")


def openai_api_key() -> str | None:
    load_env_file()
    return os.environ.get("OPENAI_API_KEY")


def openai_model() -> str:
    load_env_file()
    return os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
