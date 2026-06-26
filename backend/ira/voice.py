
import speech_recognition as sr

def start_listening():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    print("Listening for your voice...")
    print("Opening microphone...")
    with microphone as source:
        print("Adjusting for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Ready. Please speak.")
        while True:
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                command = recognizer.recognize_google(audio)
                print(f"You said: {command}")
                return command
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                print(f"Error: {e}")
                break
