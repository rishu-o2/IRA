from __future__ import annotations

import os
import re
from pathlib import Path

ENV_PAIR_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(.*?)(?=(?:[A-Za-z_][A-Za-z0-9_]*=)|$)")


def load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"

    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        clean_line = line.strip()

        if not clean_line or clean_line.startswith("#"):
            continue

        for match in ENV_PAIR_RE.finditer(clean_line):
            key = match.group(1).strip().lstrip("\ufeff")
            value = match.group(2).strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def google_api_key() -> str | None:
    load_env_file()
    return os.environ.get("GOOGLE_API_KEY")


def openai_api_key() -> str | None:
    load_env_file()
    return os.environ.get("OPENAI_API_KEY")


def gemini_api_key() -> str | None:
    load_env_file()
    return os.environ.get("GEMINI_API_KEY")


def openai_model() -> str:
    load_env_file()
    return os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def gemini_model() -> str:
    load_env_file()
    return os.environ.get("GEMINI_MODEL", "gemini-1.5-chat")
