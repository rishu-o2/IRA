from __future__ import annotations

from .assistant import IRAAssistant


def main() -> None:
    assistant = IRAAssistant()

    print("IRA is online. Type 'help' for commands or 'exit' to close.")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in {"exit", "quit", "bye"}:
            print("IRA: Going offline for now.")
            break

        response = assistant.handle(user_input)
        print(f"IRA: {response.text}")


if __name__ == "__main__":
    main()

