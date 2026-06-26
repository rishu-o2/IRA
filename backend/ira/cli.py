from __future__ import annotations

import sys
from .assistant import IRAAssistant
from .voice import VoiceAssistant

WAKE_WORDS = {"hello", "wake up", "wake", "activate", "hey ira", "hello ira", "ira"}
SLEEP_WORDS = {"go to sleep", "sleep", "deactivate", "standby"}


def is_wake_word(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in WAKE_WORDS)


def is_sleep_word(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in SLEEP_WORDS)


def main() -> None:
    assistant = IRAAssistant()
    voice_assistant = VoiceAssistant()

    # Determine initial mode from CLI flags
    voice_mode = "--voice" in sys.argv
    is_active = False  # Starts deactivated

    if voice_mode:
        if not voice_assistant.speech_enabled or not voice_assistant.tts_enabled:
            print("WARNING: Voice dependencies not fully loaded. Falling back to text mode.")
            voice_mode = False

    print("IRA is online. Type 'help' for commands or 'exit' to close.")
    if not voice_mode:
        print("Tip: Start with '--voice' flag or type 'voice' to enable voice commands.")
        print("IRA is currently asleep. Type 'hello' or 'wake up' to activate.")
    else:
        print("Voice mode active. Say 'text mode' to switch to typing, or 'exit' to quit.")
        print("IRA is currently asleep. Speak 'hello' or 'wake up' to activate.")

    while True:
        try:
            if not voice_mode:
                user_input = input("You: ").strip()
                if not user_input:
                    continue

                lowered = user_input.lower()
                if lowered in {"exit", "quit", "bye"}:
                    print("IRA: Going offline for now.")
                    if voice_assistant.tts_enabled:
                        voice_assistant.speak("Going offline for now.")
                    break

                if lowered in {"voice", "voice mode", "enable voice"}:
                    if voice_assistant.speech_enabled and voice_assistant.tts_enabled:
                        print("IRA: Switching to voice mode. Start speaking!")
                        voice_assistant.speak("Switching to voice mode.")
                        voice_mode = True
                    else:
                        print("IRA: Voice mode is unavailable. Ensure speechrecognition, sounddevice, and pyttsx3 are installed.")
                    continue

                if not is_active:
                    if is_wake_word(user_input):
                        is_active = True
                        msg = "Hello sir. I am awake and ready."
                        print(f"IRA: {msg}")
                        if voice_assistant.tts_enabled:
                            voice_assistant.speak(msg)
                    else:
                        print("IRA: [Asleep] Say 'hello' or 'wake up' to activate me.")
                else:
                    if is_sleep_word(user_input):
                        is_active = False
                        msg = "Going to sleep. Say hello or wake up to activate me."
                        print(f"IRA: {msg}")
                        if voice_assistant.tts_enabled:
                            voice_assistant.speak(msg)
                    else:
                        response = assistant.handle(user_input)
                        print(f"IRA: {response.text}")

            else:
                if not is_active:
                    print("\nYou (speak): [Asleep - listening for wake word...]", end="\r", flush=True)
                else:
                    print("\nYou (speak): [Listening...]", end="\r", flush=True)

                transcription = voice_assistant.listen(timeout=5.0, phrase_time_limit=10.0)

                # Clear the print line
                print(" " * 45, end="\r", flush=True)

                if transcription is None:
                    # Timeout, no speech heard. Just loop back.
                    continue

                if transcription == "":
                    # Heard speech but couldn't understand it
                    if is_active:
                        print("You (speak): [Speech not recognized]")
                    continue

                print(f"You: {transcription}")
                lowered = transcription.lower()

                if lowered in {"exit", "quit", "bye"}:
                    print("IRA: Going offline for now.")
                    voice_assistant.speak("Going offline for now.")
                    break

                if lowered in {"text", "text mode", "switch to text", "go to text"}:
                    print("IRA: Switching to text mode.")
                    voice_assistant.speak("Switching to text mode.")
                    voice_mode = False
                    continue

                if not is_active:
                    if is_wake_word(transcription):
                        is_active = True
                        msg = "Hello sir. I am awake and ready."
                        print(f"IRA: {msg}")
                        voice_assistant.speak(msg)
                    else:
                        # Print that it was ignored
                        print(f"You (speak): [Ignored while asleep: '{transcription}']")
                else:
                    if is_sleep_word(transcription):
                        is_active = False
                        msg = "Going to sleep. Say hello or wake up to activate me."
                        print(f"IRA: {msg}")
                        voice_assistant.speak(msg)
                    else:
                        response = assistant.handle(transcription)
                        print(f"IRA: {response.text}")
                        voice_assistant.speak(response.text)

        except KeyboardInterrupt:
            if voice_mode:
                print("\nIRA: Ctrl+C detected. Switching to text mode.")
                voice_assistant.speak("Switching to text mode.")
                voice_mode = False
            else:
                print("\nIRA: Going offline for now.")
                if voice_assistant.tts_enabled:
                    voice_assistant.speak("Going offline for now.")
                break


if __name__ == "__main__":
    main()



