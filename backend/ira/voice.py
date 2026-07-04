from __future__ import annotations

import wave
import io
import time
import wave
import logging
import speech_recognition as sr
import os

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Cache the selected microphone index to avoid scanning on every request
_cached_mic_index: int | None = None


def get_working_microphone() -> sr.Microphone:
    """Return a microphone object.

    Tries an explicit ``MIC_INDEX`` environment variable, then the default
    microphone, and finally falls back to the first listed device. Detailed
    logging helps identify which device is being used on Windows.
    """
    mic_index = os.getenv("MIC_INDEX")
    if mic_index is not None:
        try:
            return sr.Microphone(device_index=int(mic_index))
        except Exception as e:
            logger.warning(f"Invalid MIC_INDEX '{mic_index}': {e}. Falling back to default microphone.")
    # Try the default microphone first
    try:
        mic = sr.Microphone()
        logger.info("Using default microphone.")
        return mic
    except Exception as e:
        logger.warning(f"Default microphone failed: {e}")
    # Fallback: list microphones and pick the first one
    try:
        names = sr.Microphone.list_microphone_names()
        if names:
            logger.info(f"Falling back to first listed microphone (index 0): {names[0]}")
            return sr.Microphone(device_index=0)
    except Exception as e:
        logger.warning(f"Could not list microphones: {e}")
    raise RuntimeError("No working microphone found")


def list_available_microphones() -> list[str]:
    """Return a list of microphone names available via SpeechRecognition."""
    try:
        names = sr.Microphone.list_microphone_names()
        logger.info(f"Available microphones: {names}")
        return names
    except Exception as e:
        logger.warning(f"Could not list microphones: {e}")
        return []



def record_via_sounddevice(duration: float = 10.0, sample_rate: int = 16000) -> sr.AudioData | None:
    """Record audio using sounddevice and return a SpeechRecognition AudioData object.
    Returns ``None`` if recording fails.
    """
    try:
        import numpy as np
        import sounddevice as sd
    except Exception as e:
        logger.error(f"Sounddevice fallback unavailable: {e}")
        return None
    # Allow user to specify device via env var
    env_index = os.getenv("SD_DEVICE_INDEX")
    if env_index is not None:
        try:
            default_input = int(env_index)
            logger.info(f"Using sounddevice device from SD_DEVICE_INDEX env var: {default_input}")
        except Exception as e:
            logger.warning(f"Invalid SD_DEVICE_INDEX '{env_index}': {e}")
            default_input = None
    else:
        default_input = None
    # Determine an input device with channels > 0
    if default_input is None:
        try:
            # Try system default
            default_input = sd.default.device[0]
            if default_input is None or sd.query_devices(default_input)['max_input_channels'] == 0:
                raise ValueError("Default device has no input channels")
            logger.info(f"Using sounddevice default input device index: {default_input}")
        except Exception:
            # Find first suitable input device
            devices = sd.query_devices()
            candidate = None
            for dev in devices:
                if dev['max_input_channels'] > 0:
                    candidate = dev['index']
                    break
            if candidate is None:
                logger.error("No sounddevice input device found")
                return None
            default_input = candidate
            logger.info(f"Selected sounddevice input device index: {default_input}")
    try:
        logger.info(f"Recording {duration}s audio via sounddevice at {sample_rate}Hz on device {default_input}")
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16', device=default_input)
        sd.wait()
        logger.debug(f"Recorded shape: {recording.shape}, dtype: {recording.dtype}")
        audio_bytes = recording.tobytes()
        logger.debug(f"Recorded {len(audio_bytes)} bytes")
        # Save to WAV for debugging purposes
        try:
            wav_path = os.path.join(os.getcwd(), "last_recording.wav")
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit = 2 bytes
                wf.setframerate(sample_rate)
                wf.writeframes(audio_bytes)
            logger.info(f"Saved recorded audio to {wav_path}")
        except Exception as e:
            logger.warning(f"Failed to save WAV file: {e}")
        return sr.AudioData(audio_bytes, sample_rate, 2)
    except Exception as e:
        logger.error(f"Sounddevice recording failed: {e}")
        return None


def listen_for_command(timeout: float = 6.0, phrase_time_limit: float = 10.0) -> str | None:
    """Listens using speech_recognition and transcribes using Google Cloud Speech API.
    Tries the PyAudio microphone first; if unavailable, falls back to sounddevice.
    """
    # Debug: list available microphones (PyAudio)
    try:
        names = list_available_microphones()
        logger.debug(f"PyAudio microphones detected ({len(names)}): {names}")
    except Exception as e:
        logger.debug(f"Failed to list PyAudio microphones: {e}")
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    audio = None
    # Try PyAudio microphone
    try:
        mic = get_working_microphone()
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("Listening using PyAudio...")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
    except Exception as e:
        logger.warning(f"PyAudio microphone failed ({e}); falling back to sounddevice.")
        audio = record_via_sounddevice(duration=phrase_time_limit)
    if audio is None:
        logger.warning("No audio captured from either PyAudio or sounddevice.")
        return None
    try:
        # Primary: Google Web Speech API (requires internet)
        text = recognizer.recognize_google(audio)
        return text.strip()
    except Exception as e:
        logger.warning(f"Google recognition failed: {e}. Trying offline recognizer.")
        try:
            # Offline fallback using PocketSphinx if available
            text = recognizer.recognize_sphinx(audio)
            return text.strip()
        except Exception as e2:
            logger.error(f"Offline recognition also failed: {e2}")
            return None




class VoiceAssistant:
    def __init__(self) -> None:
        self.speech_enabled = True  # Enable speech by default; we'll handle missing deps gracefully
        self.tts_enabled = False
        
        # Attempt to import optional sounddevice and numpy for advanced features
        try:
            import numpy as np
            import sounddevice as sd
            self.np = np
            self.sd = sd
        except Exception as e:
            logger.info(f"Optional audio libraries not available: {e}. Continuing without them.")
        
        # speech_recognition is required for basic listening; it's already installed
        self.sr = sr
        self.recognizer = sr.Recognizer()
        
        # Attempt to initialize pyttsx3 for TTS
        try:
            import pyttsx3
            self.pyttsx3 = pyttsx3
            engine = self.pyttsx3.init()
            del engine
            self.tts_enabled = True
        except Exception as e:
            logger.warning(f"TTS initialization failed: {e}.")

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
