from __future__ import annotations

import sys
import pytest
from types import SimpleNamespace
from ira.voice import VoiceAssistant


def test_voice_assistant_disabled_when_missing_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    # Simulate missing modules
    monkeypatch.setitem(sys.modules, "speech_recognition", None)
    monkeypatch.setitem(sys.modules, "sounddevice", None)
    monkeypatch.setitem(sys.modules, "pyttsx3", None)

    va = VoiceAssistant()
    assert va.speech_enabled is False
    assert va.tts_enabled is False


def test_voice_assistant_enabled_when_modules_present(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock speech_recognition
    fake_sr = SimpleNamespace(
        Recognizer=lambda: SimpleNamespace(dynamic_energy_threshold=False, energy_threshold=0),
        Microphone=object
    )
    fake_sd = SimpleNamespace()
    
    # Mock pyttsx3
    class FakeEngine:
        def getProperty(self, prop: str) -> list:
            return []
        def setProperty(self, prop: str, value: object) -> None:
            pass
        def say(self, text: str) -> None:
            pass
        def runAndWait(self) -> None:
            pass

    fake_pyttsx3 = SimpleNamespace(
        init=lambda: FakeEngine()
    )

    monkeypatch.setitem(sys.modules, "speech_recognition", fake_sr)
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)
    monkeypatch.setitem(sys.modules, "pyttsx3", fake_pyttsx3)

    va = VoiceAssistant()
    assert va.speech_enabled is True
    assert va.tts_enabled is True


def test_wake_and_sleep_words() -> None:
    from ira.cli import is_wake_word, is_sleep_word

    # Test wake words
    assert is_wake_word("Hello") is True
    assert is_wake_word("wake up") is True
    assert is_wake_word("hey ira, what time is it?") is True
    assert is_wake_word("ira") is True
    assert is_wake_word("tell me a joke") is False

    # Test sleep words
    assert is_sleep_word("go to sleep") is True
    assert is_sleep_word("deactivate") is True
    assert is_sleep_word("standby") is True
    assert is_sleep_word("open website google.com") is False

