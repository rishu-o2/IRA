"""
normalizer.py – Command normalization and input classification.

Extracted from IRAAssistant._normalize_command,
_looks_sensitive_or_unsupported, _looks_like_website, _is_known_folder.

No IRA business logic.  No imports from assistant.py.
"""
from __future__ import annotations


# Polite prefixes stripped before routing.
_PREFIXES: tuple[str, ...] = (
    "hey ira, ", "hey ira ", "hey, ira ", "hey, ", "hey ",
    "hello ira, ", "hello ira ", "hello, ira ", "hello, ", "hello ",
    "hi ira, ", "hi ira ", "hi, ira ", "hi, ", "hi ",
    "please ", "can you ", "could you ", "would you ", "ira, ", "ira ", "ira: ",
)

_SUFFIXES: tuple[str, ...] = (
    " please", " thank you", " thanks", " now", " for me",
)

# Commands that reference sensitive or not-yet-supported capabilities.
_SENSITIVE_PREFIXES: tuple[str, ...] = (
    "send message",
    "send email",
    "email ",
    "call ",
    "delete ",
    "remove ",
    "move ",
    "buy ",
    "purchase ",
    "pay ",
    "transfer ",
)

_KNOWN_FOLDERS: frozenset[str] = frozenset({
    "desktop", "downloads", "download",
    "documents", "document",
    "pictures", "photos",
    "music", "videos",
})


class CommandNormalizer:
    """Strips conversational noise from raw user input and classifies it."""

    def normalize(self, message: str) -> str:
        """Strip prefixes, suffixes, and collapse whitespace."""
        command = " ".join(message.strip().split())

        changed = True
        while changed:
            changed = False
            lowered = command.lower()
            for prefix in _PREFIXES:
                if lowered.startswith(prefix):
                    command = command[len(prefix):].strip()
                    changed = True
                    break
            if changed:
                continue
            for suffix in _SUFFIXES:
                if command.lower().endswith(suffix):
                    command = command[: -len(suffix)].strip()
                    changed = True
                    break

        return command

    def looks_sensitive_or_unsupported(self, lowered: str) -> bool:
        """Return True when the command targets a not-yet-supported capability."""
        return lowered.startswith(_SENSITIVE_PREFIXES)

    def looks_like_website(self, target: str) -> bool:
        lowered = target.lower()
        return lowered.startswith(("http://", "https://")) or "." in lowered

    def is_known_folder(self, target: str) -> bool:
        return target.lower().strip() in _KNOWN_FOLDERS


# Module-level singleton for convenience.
default_normalizer: CommandNormalizer = CommandNormalizer()
