from __future__ import annotations

import io
import time
import wave
import logging
import speech_recognition as sr

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Cache the selected microphone index to avoid scanning on every request
_cached_mic_index: int | None = None


def get_working_microphone() -> sr.Microphone:
    """Finds the best working microphone input device with signal, caching the result."""
    global _cached_mic_index
    if _cached_mic_index is not None:
        return sr.Microphone(device_index=_cached_mic_index)

    try:
        import pyaudio
        import numpy as np
        p = pyaudio.PyAudio()
    except ImportError:
        return sr.Microphone()

    best_index = None
    best_rms = -1.0
    
    try:
        for i in range(p.get_device_count()):
            try:
                dev_info = p.get_device_info_by_index(i)
                if dev_info.get('maxInputChannels', 0) > 0:
                    # Open a small stream to read 0.05 seconds of audio
                    stream = p.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=16000,
                        input=True,
                        input_device_index=i,
                        frames_per_buffer=512
                    )
                    data = stream.read(800, exception_on_overflow=False)
                    stream.close()
                    
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    rms = float(np.sqrt(np.mean(audio_data.astype(np.float64)**2)))
                    
                    if rms > best_rms:
                        best_rms = rms
                        best_index = i
            except Exception:
                continue
    except Exception as e:
        logger.error(f"Error scanning microphones: {e}")
    finally:
        p.terminate()

    if best_index is not None:
        _cached_mic_index = best_index
        logger.info(f"Selected microphone index {best_index} (RMS Energy: {best_rms:.2f})")
        return sr.Microphone(device_index=best_index)
        
    return sr.Microphone()


def listen_for_command(timeout: float = 6.0, phrase_time_limit: float = 10.0) -> str | None:
    """Listens using speech_recognition and transcribes using Google Cloud Speech API."""
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    try:
        mic = get_working_microphone()
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("Listening...")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            text = recognizer.recognize_google(audio)
            return text.strip()
    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        logger.error(f"Error in speech listener: {e}")
        return None


class VoiceAssistant:
    def __init__(self) -> None:
        self.speech_enabled = False
        self.tts_enabled = False

        # Attempt to import sounddevice, numpy, and speech_recognition
        try:
            import numpy as np
            import sounddevice as sd
            
            self.np = np
            self.sd = sd
            self.sr = sr
            self.recognizer = sr.Recognizer()
            self.speech_enabled = True
        except ImportError as e:
            logger.warning(f"Voice input dependencies not fully installed: {e}. Voice input will not be available.")

        # Attempt to initialize pyttsx3
        try:
            import pyttsx3
            self.pyttsx3 = pyttsx3
            # Initialize once to verify driver works
            engine = self.pyttsx3.init()
            del engine
            self.tts_enabled = True
        except ImportError:
            logger.warning("pyttsx3 is not installed. Text-to-speech output will not be available.")
        except Exception as e:
            logger.warning(f"Failed to initialize pyttsx3: {e}. TTS output will not be available.")

    def speak(self, text: str) -> None:
        """Speaks the text using pyttsx3 with a female voice preference if available."""
        if not self.tts_enabled:
            return

        try:
            engine = self.pyttsx3.init()
            
            # Try to find a female voice (similar to Samantha / Zira)
            voices = engine.getProperty("voices")
            female_voice = None
            for voice in voices:
                name_lower = voice.name.lower()
                if any(x in name_lower for x in ("zira", "hazel", "susan", "samantha", "female", "woman", "elena")):
                    female_voice = voice
                    break
            
            if female_voice:
                engine.setProperty("voice", female_voice.id)
            elif voices:
                engine.setProperty("voice", voices[0].id)
                
            # Set rate (speed of speech) - default is usually around 200, 175 is natural
            engine.setProperty("rate", 175)
            engine.setProperty("volume", 1.0)
            
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            logger.error(f"Error in TTS speak: {e}")

    def listen(self, timeout: float = 6.0, phrase_time_limit: float = 10.0) -> str | None:
        """Listens using speech_recognition and transcribes via Google Cloud Speech API."""
        if not self.speech_enabled:
            print("Speech recognition is disabled. Ensure speechrecognition, sounddevice, and numpy are installed.")
            return None
        return listen_for_command(timeout=timeout, phrase_time_limit=phrase_time_limit)
