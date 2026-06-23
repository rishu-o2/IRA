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
