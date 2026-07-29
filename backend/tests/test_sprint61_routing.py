import pytest
from ira.assistant import IRAAssistant

# We use the real IRAAssistant but fake the conversation fallback
# to prove commands are handled by skills and not by the LLM.
class FakeConversation:
    def reply(self, message: str) -> str:
        return "I am the LLM fallback."

@pytest.fixture
def assistant(monkeypatch):
    # Mock system/app actions so we don't actually open apps or shutdown during tests
    monkeypatch.setattr("ira.actions.open_app", lambda app: f"Opening {app}")
    monkeypatch.setattr("ira.actions.open_known_folder", lambda folder: f"Opening folder {folder}")
    monkeypatch.setattr("ira.actions.open_website", lambda url: f"Opening {url}")
    monkeypatch.setattr("ira.actions.search_web", lambda query: f"Searching Google for {query}")
    monkeypatch.setattr("ira.actions.lock_screen", lambda: "Locking the screen.")
    monkeypatch.setattr("ira.actions.set_brightness", lambda level: f"Screen brightness set to {level}%.")
    monkeypatch.setattr("ira.actions.volume_up", lambda: "Increasing volume.")
    monkeypatch.setattr("ira.actions.volume_down", lambda: "Decreasing volume.")
    monkeypatch.setattr("ira.actions.mute_system", lambda: "Muting the volume.")
    monkeypatch.setattr("ira.actions.get_battery_status", lambda: "Battery is at 100%.")
    monkeypatch.setattr("ira.actions.play_pause_media", lambda: "Toggling media playback.")

    conv = FakeConversation()
    return IRAAssistant(conversation=conv)


def test_time(assistant):
    res = assistant.handle("What time is it?")
    assert res.handled is True
    assert "The current time is" in res.text

def test_date(assistant):
    res = assistant.handle("What is today's date?")
    assert res.handled is True
    assert "Today is" in res.text

def test_battery(assistant):
    res = assistant.handle("Battery status")
    assert res.handled is True
    assert "Battery is at" in res.text

def test_volume_up(assistant):
    res = assistant.handle("Volume up")
    assert res.handled is True
    assert "Increasing volume" in res.text

def test_volume_down(assistant):
    res = assistant.handle("Volume down")
    assert res.handled is True
    assert "Decreasing volume" in res.text

def test_mute(assistant):
    res = assistant.handle("Mute")
    assert res.handled is True
    assert "Muting" in res.text

def test_lock_screen(assistant):
    res = assistant.handle("Lock screen")
    assert res.handled is True
    assert "Locking the screen" in res.text

def test_brightness(assistant):
    res = assistant.handle("Set brightness to 50")
    assert res.handled is True
    assert "brightness set to 50%" in res.text

def test_memory_store_and_recall_favourite(assistant):
    # Store
    res1 = assistant.handle("Remember my favourite IDE is VS Code")
    assert res1.handled is True

    # Recall (UK spelling)
    res2 = assistant.handle("What is my favourite IDE?")
    assert res2.handled is True
    assert "VS Code" in res2.text or "vs code" in res2.text.lower()

def test_open_chrome(assistant):
    res = assistant.handle("Open Chrome")
    assert res.handled is True
    assert "Opening" in res.text
    assert "chrome" in res.text.lower()

def test_open_vscode(assistant):
    res = assistant.handle("Open VS Code")
    assert res.handled is True
    assert "Opening" in res.text
    assert "code" in res.text.lower()

def test_open_downloads(assistant):
    res = assistant.handle("Open Downloads")
    assert res.handled is True
    assert "Opening folder downloads" in res.text

def test_open_youtube_browser(assistant):
    res = assistant.handle("Open YouTube")
    assert res.handled is True
    assert "Opening https://youtube.com" in res.text

def test_open_github(assistant):
    res = assistant.handle("Open GitHub")
    assert res.handled is True
    assert "Opening https://github.com" in res.text

def test_search_web(assistant):
    res = assistant.handle("Search for Python tutorials")
    assert res.handled is True
    assert "Searching Google for" in res.text

def test_play_media(assistant):
    res = assistant.handle("Play music")
    assert res.handled is True
    assert "Toggling media playback" in res.text
