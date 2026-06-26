from ira.assistant import IRAAssistant


class FakeConversation:
    def __init__(self, text: str = "API reply") -> None:
        self.text = text
        self.messages: list[str] = []

    def reply(self, message: str) -> str:
        self.messages.append(message)
        return self.text


def test_greeting_response() -> None:
    conversation = FakeConversation("Hello from API.")
    assistant = IRAAssistant(conversation=conversation)

    response = assistant.handle("hello")

    assert response.handled is True
    assert response.text == "Hello from API."
    assert conversation.messages == ["hello"]


def test_unknown_command_is_not_handled() -> None:
    assistant = IRAAssistant()

    response = assistant.handle("send message to alex")

    assert response.handled is False
    assert "cannot complete" in response.text.lower()


def test_open_ira_greeting() -> None:
    assistant = IRAAssistant()

    response = assistant.handle("open IRA")

    assert response.handled is True
    assert "awake" in response.text.lower()


def test_wake_laptop_greeting() -> None:
    assistant = IRAAssistant()

    response = assistant.handle("wake my laptop")

    assert response.handled is True
    assert "awake" in response.text.lower()


def test_general_conversation_uses_api() -> None:
    conversation = FakeConversation("I am doing well.")
    assistant = IRAAssistant(conversation=conversation)

    response = assistant.handle("how are you")

    assert response.handled is True
    assert response.text == "I am doing well."
    assert conversation.messages == ["how are you"]


def test_launch_alias_opens_app(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr("ira.actions._find_start_menu_shortcut", lambda app_name: None)
    monkeypatch.setattr("ira.actions._find_registered_app", lambda command: None)
    monkeypatch.setattr("ira.actions.shutil.which", lambda command: "C:\\Program Files\\Google\\Chrome\\chrome.exe")
    monkeypatch.setattr("ira.actions.os.startfile", calls.append)

    response = IRAAssistant().handle("launch google chrome")

    assert response.handled is True
    assert response.text == "Opening google chrome"
    assert calls == ["C:\\Program Files\\Google\\Chrome\\chrome.exe"]


def test_unknown_app_is_not_reported_as_opened(monkeypatch) -> None:
    monkeypatch.setattr("ira.actions._find_start_menu_shortcut", lambda app_name: None)
    monkeypatch.setattr("ira.actions._find_registered_app", lambda command: None)
    monkeypatch.setattr("ira.actions.shutil.which", lambda command: None)

    response = IRAAssistant().handle("open definitelynotarealapp123")

    assert response.handled is False
    assert "could not find" in response.text.lower()


def test_open_application_phrase_opens_app(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr("ira.actions._find_start_menu_shortcut", lambda app_name: None)
    monkeypatch.setattr("ira.actions._find_registered_app", lambda command: "C:\\Windows\\System32\\notepad.exe")
    monkeypatch.setattr("ira.actions.os.startfile", calls.append)

    response = IRAAssistant().handle("open application notepad")

    assert response.handled is True
    assert response.text == "Opening notepad"
    assert calls == ["C:\\Windows\\System32\\notepad.exe"]


def test_go_to_alias_opens_website(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr("ira.actions.webbrowser.open", calls.append)

    response = IRAAssistant().handle("go to youtube.com")

    assert response.handled is True
    assert response.text == "Opening https://youtube.com"
    assert calls == ["https://youtube.com"]


def test_natural_search_opens_google(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr("ira.actions.webbrowser.open", calls.append)

    response = IRAAssistant().handle("please search for python tutorials")

    assert response.handled is True
    assert response.text == "Searching Google for python tutorials"
    assert calls == ["https://www.google.com/search?q=python+tutorials"]


def test_open_website_from_plain_open(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr("ira.actions.webbrowser.open", calls.append)

    response = IRAAssistant().handle("can you open youtube.com")

    assert response.handled is True
    assert response.text == "Opening https://youtube.com"
    assert calls == ["https://youtube.com"]


def test_play_on_youtube_suffix(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr("ira.actions.webbrowser.open", calls.append)

    response = IRAAssistant().handle("play relaxing music on YouTube")

    assert response.handled is True
    assert response.text == "Searching YouTube for relaxing music"
    assert calls == ["https://www.youtube.com/results?search_query=relaxing+music"]


def test_recursive_command_normalization() -> None:
    assistant = IRAAssistant()
    
    # Prefix only
    assert assistant._normalize_command("hey ira open notepad") == "open notepad"
    # Prefix and suffix
    assert assistant._normalize_command("hey ira, please open notepad please") == "open notepad"
    # Nested prefixes/suffixes
    assert assistant._normalize_command("hello, hey, ira could you please wake up please thanks") == "wake up"


def test_volume_actions(monkeypatch) -> None:
    volume_calls = []
    monkeypatch.setattr("ira.actions.os.name", "nt")
    monkeypatch.setattr("ira.actions.ctypes.windll.user32.keybd_event", lambda *args: volume_calls.append(args))
    
    assistant = IRAAssistant()
    
    # Test Volume Up
    res_up = assistant.handle("hey ira volume up please")
    assert res_up.handled is True
    assert "Increasing volume" in res_up.text
    assert len(volume_calls) == 2 # Press and Release

    # Test Volume Down
    volume_calls.clear()
    res_down = assistant.handle("hey ira decrease volume")
    assert res_down.handled is True
    assert "Decreasing volume" in res_down.text
    assert len(volume_calls) == 2 # Press and Release


def test_brightness_control(monkeypatch) -> None:
    cmd_runs = []
    monkeypatch.setattr("ira.actions.os.name", "nt")
    monkeypatch.setattr("ira.actions.subprocess.run", lambda cmd, **kwargs: cmd_runs.append(cmd))
    
    assistant = IRAAssistant()
    res = assistant.handle("set brightness to 75%")
    
    assert res.handled is True
    assert "Screen brightness set to 75%" in res.text
    assert len(cmd_runs) == 1
    assert "WmiSetBrightness(0, 75)" in cmd_runs[0]


def test_battery_and_system_stats(monkeypatch) -> None:
    monkeypatch.setattr("ira.assistant.get_battery_status", lambda: "Battery is at 88%, and is currently charging.")
    monkeypatch.setattr("ira.assistant.get_system_stats", lambda: "CPU usage is at 12.5%, and RAM memory usage is at 45.2%. Battery is at 88%, and is currently charging.")
    
    assistant = IRAAssistant()
    
    # Test Battery
    res_batt = assistant.handle("battery status")
    assert res_batt.handled is True
    assert "Battery is at 88%" in res_batt.text
    
    # Test System Stats
    res_stats = assistant.handle("system stats")
    assert res_stats.handled is True
    assert "CPU usage is at 12.5%" in res_stats.text
    assert "RAM memory usage is at 45.2%" in res_stats.text


def test_virtual_world_actions() -> None:
    assistant = IRAAssistant()
    
    # Verify initial mood state
    assert assistant.virtual_world.state["mood"] == "helpful"
    
    # Change mood
    res_mood = assistant.handle("change mood to energetic")
    assert res_mood.handled is True
    assert "mood is now energetic" in res_mood.text.lower()
    assert assistant.virtual_world.state["mood"] == "energetic"
    
    # Add to Knowledge Base
    res_kb = assistant.handle("add knowledge python web frameworks")
    assert res_kb.handled is True
    assert "python web frameworks" in assistant.virtual_world.state["knowledge_base"]
    
    # Query Virtual Status
    res_status = assistant.handle("virtual status")
    assert res_status.handled is True
    assert "mood: energetic" in res_status.text.lower()


def test_recent_modifications() -> None:
    assistant = IRAAssistant()

    # Initially, modification history is empty
    res_empty = assistant.handle("what did you update")
    assert res_empty.handled is True
    assert "not made any modifications" in res_empty.text

    # Simulate a write self-modification
    assistant._apply_self_modifications('<write_file path="test_file.txt">content</write_file>')
    
    # Query updates again
    res_updates = assistant.handle("recent modifications")
    assert res_updates.handled is True
    assert "test_file.txt" in res_updates.text
    assert "write" in res_updates.text

    # Cleanup the created test file if it exists
    import os
    from pathlib import Path
    project_root = Path(__file__).resolve().parents[2]
    test_file_path = project_root / "test_file.txt"
    if test_file_path.exists():
        os.remove(test_file_path)


