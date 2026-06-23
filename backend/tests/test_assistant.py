from ira.assistant import IRAAssistant


def test_greeting_response() -> None:
    assistant = IRAAssistant()

    response = assistant.handle("hello")

    assert response.handled is True
    assert "IRA is online" in response.text


def test_unknown_command_is_not_handled() -> None:
    assistant = IRAAssistant()

    response = assistant.handle("send message to alex")

    assert response.handled is False
    assert "open apps" in response.text


def test_launch_alias_opens_app(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr("ira.actions.subprocess.Popen", lambda command, shell: calls.append(command))

    response = IRAAssistant().handle("launch google chrome")

    assert response.handled is True
    assert response.text == "Opening google chrome"
    assert calls == ["chrome"]


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
