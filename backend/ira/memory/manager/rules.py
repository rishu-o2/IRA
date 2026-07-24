from __future__ import annotations


class MemoryRules:
    _GREETINGS = {
        "hello",
        "hi",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
    }
    _ACKNOWLEDGEMENTS = {
        "thanks",
        "thank you",
        "okay",
        "ok",
        "great",
        "cool",
        "nice",
        "awesome",
    }
    _TEMPORARY_COMMAND_PREFIXES = (
        "open ",
        "search ",
        "play ",
        "lock ",
        "close ",
        "launch ",
        "start ",
        "stop ",
        "turn on ",
        "turn off ",
    )
    _QUESTION_PREFIXES = (
        "what ",
        "who ",
        "when ",
        "where ",
        "why ",
        "how ",
        "explain ",
        "tell me ",
        "define ",
    )
    _MEMORY_SIGNALS = (
        "my favorite ",
        "my exam is ",
        "i prefer ",
        "i use ",
        "i am ",
        "i'm ",
        "i live in ",
        "i work as ",
        "i work at ",
        "i want to ",
        "i'm building ",
        "i am building ",
        "i'm preparing ",
        "i am preparing ",
        "always ",
        "don't ",
        "do not ",
        "respond ",
        "call me ",
        "my project is ",
        "i switched to ",
    )

    def should_remember(self, text: str) -> bool:
        normalized = self.normalize(text)
        if not normalized:
            return False
        if self.is_ignored(normalized):
            return False
        return any(signal in normalized for signal in self._MEMORY_SIGNALS)

    def is_ignored(self, text: str) -> bool:
        normalized = self.normalize(text)
        return (
            normalized in self._GREETINGS
            or normalized in self._ACKNOWLEDGEMENTS
            or normalized.startswith(self._TEMPORARY_COMMAND_PREFIXES)
            or normalized.endswith("?")
            or normalized.startswith(self._QUESTION_PREFIXES)
        )

    def normalize(self, text: str) -> str:
        return " ".join(text.strip().casefold().split())
