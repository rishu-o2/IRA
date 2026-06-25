from __future__ import annotations

import io
import time
import wave
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class VoiceAssistant:
    def __init__(self) -> None:
        self.speech_enabled = False
        self.tts_enabled = False

        # Attempt to import sounddevice, numpy, and speech_recognition
        try:
            import numpy as np
            import sounddevice as sd
            import speech_recognition as sr
            
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
        """Listens using sounddevice (custom VAD) and transcribes using speech_recognition."""
        if not self.speech_enabled:
            print("Speech recognition is disabled. Ensure speechrecognition, sounddevice, and numpy are installed.")
            return None

        sample_rate = 16000
        # Check volume in 100ms chunks
        chunk_size = int(sample_rate * 0.1)

        # 1. Calibrate background noise level
        try:
            # We record a quick 0.3-second sample of background noise to auto-calibrate threshold
            background_sample = self.sd.rec(int(sample_rate * 0.3), samplerate=sample_rate, channels=1, dtype='int16')
            self.sd.wait()
            background_rms = self.np.sqrt(self.np.mean(background_sample.astype(self.np.float64)**2))
            # Set speech threshold relative to background noise
            # Minimum baseline of 350 to avoid reading complete silence as speech
            silence_threshold = max(background_rms * 2.2, 350.0)
        except Exception as e:
            logger.error(f"Failed to calibrate microphone: {e}")
            silence_threshold = 400.0

        recorded_chunks = []
        is_speaking = False
        silence_start_time = None
        start_time = time.time()
        max_silence_duration = 1.6 # seconds of silence before stopping

        try:
            # Open the audio stream
            with self.sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16') as stream:
                while True:
                    # Read chunk from mic
                    chunk, overflowed = stream.read(chunk_size)
                    recorded_chunks.append(chunk)

                    # Calculate volume (RMS)
                    rms = self.np.sqrt(self.np.mean(chunk.astype(self.np.float64)**2))

                    if rms > silence_threshold:
                        if not is_speaking:
                            is_speaking = True
                        silence_start_time = None
                    else:
                        if is_speaking:
                            if silence_start_time is None:
                                silence_start_time = time.time()
                            elif time.time() - silence_start_time > max_silence_duration:
                                break

                    # Timeout limits
                    now = time.time()
                    if now - start_time > phrase_time_limit:
                        break
                    
                    if not is_speaking and now - start_time > timeout:
                        # User didn't say anything
                        return None

            # If we didn't capture any speech, return None
            if not is_speaking or not recorded_chunks:
                return None

            # Concatenate chunks
            audio_data_np = self.np.concatenate(recorded_chunks, axis=0)

            # Build a WAV file in memory
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2) # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data_np.tobytes())
            wav_io.seek(0)

            # Transcribe WAV file via speech_recognition
            with self.sr.AudioFile(wav_io) as source:
                audio_data = self.recognizer.record(source)
                
            text = self.recognizer.recognize_google(audio_data)
            return text.strip()

        except self.sr.UnknownValueError:
            # Speech heard but not recognized
            # Return empty string to signify recognized but empty
            return ""
        except self.sr.RequestError as e:
            print(f"Speech recognition service error: {e}")
            return None
        except Exception as e:
            print(f"Error during audio capture/recognition: {e}")
            return None
