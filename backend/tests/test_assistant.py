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
    assert "do not know" in response.text

