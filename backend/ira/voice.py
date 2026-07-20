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

import ctranslate2
from faster_whisper import WhisperModel
import tempfile

_has_gpu = False
try:
    if hasattr(ctranslate2, "get_cuda_device_count") and ctranslate2.get_cuda_device_count() > 0:
        _has_gpu = True
except Exception:
    pass

_device = "cuda" if _has_gpu else "cpu"
_compute_type = "float16" if _has_gpu else "int8"

print("Device:", _device)
print("Compute:", _compute_type)
print("CUDA devices:", ctranslate2.get_cuda_device_count())

try:
    _whisper_model = WhisperModel(
        "tiny.en",
        device=_device,
        compute_type=_compute_type,
    )
    print("[WHISPER] Model loaded")
except Exception as e:
    print(f"[WHISPER ERROR] Failed to load model: {e}")
    _whisper_model = None

print(f"[VOICE MODULE] Loaded from: {__file__}")

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
    """Record audio using sounddevice.InputStream with voice activity detection.

    Buffers audio continuously and stops after approximately 0.7 seconds of
    silence once speech has been detected, or after a hard cap of 8 seconds.
    Returns a SpeechRecognition AudioData object, or None if recording fails.

    The ``duration`` parameter is kept for signature compatibility but is not
    used as a fixed recording window.
    """
    try:
        import numpy as np
        import sounddevice as sd
    except Exception as e:
        logger.error(f"Sounddevice fallback unavailable: {e}")
        return None

    # --- VAD tuning constants ---
    MAX_SECONDS       = 8.0    # hard cap on total recording time
    SILENCE_SECONDS   = 0.7    # consecutive silence required to stop after speech
    CHUNK_SECONDS     = 0.05   # size of each audio chunk (50 ms)
    RMS_SPEECH_THRESH = 300    # RMS level above which audio counts as speech
    # (int16 range 0–32767; 300 is a conservative floor for human speech)

    chunk_frames          = int(CHUNK_SECONDS * sample_rate)
    max_chunks            = int(MAX_SECONDS / CHUNK_SECONDS)
    silence_chunks_needed = int(SILENCE_SECONDS / CHUNK_SECONDS)

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

    # Determine an input device with at least one input channel
    if default_input is None:
        try:
            default_input = sd.default.device[0]
            if default_input is None or sd.query_devices(default_input)['max_input_channels'] == 0:
                raise ValueError("Default device has no input channels")
            logger.info(f"Using sounddevice default input device index: {default_input}")
        except Exception:
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

    logger.info(
        f"VAD InputStream recording on device {default_input} at {sample_rate} Hz "
        f"(max {MAX_SECONDS}s, silence {SILENCE_SECONDS}s, RMS thresh {RMS_SPEECH_THRESH})"
    )

    # Shared state accessed inside the callback
    all_chunks: list     = []
    silence_count: list  = [0]        # use list so the callback can mutate it
    speech_detected: list = [False]
    stop_flag: list      = [False]

    def _callback(indata, frames, time_info, status):
        """Called by sounddevice for every chunk_frames of audio."""
        if stop_flag[0]:
            raise sd.CallbackStop()

        chunk = indata.copy()
        rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))

        all_chunks.append(chunk)

        if rms >= RMS_SPEECH_THRESH:
            if not speech_detected[0]:
                print("[VOICE] Speech detected")
            speech_detected[0] = True
            silence_count[0]   = 0
        else:
            if speech_detected[0]:
                silence_count[0] += 1
                if silence_count[0] >= silence_chunks_needed:
                    print("[VOICE] Silence detected")
                    stop_flag[0] = True
                    raise sd.CallbackStop()

    try:
        rec_start = time.perf_counter()
        print("[VOICE] Waiting for speech")

        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            blocksize=chunk_frames,
            device=default_input,
            callback=_callback,
        ):
            # Block until silence stop or max time reached
            elapsed = 0.0
            poll_interval = CHUNK_SECONDS  # check at chunk resolution
            while not stop_flag[0] and elapsed < MAX_SECONDS:
                time.sleep(poll_interval)
                elapsed = time.perf_counter() - rec_start

        rec_end = time.perf_counter()
        rec_ms  = (rec_end - rec_start) * 1000
        print("[VOICE] Recording stopped")
        print(f"[PERF] Recording duration: {rec_ms:.0f} ms")

        if not speech_detected[0]:
            logger.warning("VAD: no speech detected within the recording window.")
            return None

        recording  = np.concatenate(all_chunks, axis=0)
        audio_bytes = recording.tobytes()
        logger.debug(f"VAD recorded shape: {recording.shape}, dtype: {recording.dtype}, bytes: {len(audio_bytes)}")

        # Save to WAV for debugging purposes
        try:
            wav_path = os.path.join(os.getcwd(), "last_recording.wav")
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)   # 16-bit = 2 bytes
                wf.setframerate(sample_rate)
                wf.writeframes(audio_bytes)
            logger.info(f"Saved VAD audio to {wav_path}")
        except Exception as e:
            logger.warning(f"Failed to save WAV file: {e}")

        return sr.AudioData(audio_bytes, sample_rate, 2)

    except Exception as e:
        logger.error(f"Sounddevice InputStream VAD recording failed: {e}")
        return None


def listen_for_command(timeout: float = 6.0, phrase_time_limit: float = 10.0) -> str | None:
    """Listens using speech_recognition and transcribes using Google Cloud Speech API.
    Tries the PyAudio microphone first; if unavailable, falls back to sounddevice.
    """
    print("========== ENTERED listen_for_command ==========")
    total_start = time.perf_counter()
    print("[PERF] Entering listen_for_command")
    print("[VOICE] Entered listen_for_command()")
    # Debug: list available microphones (PyAudio)
    try:
        names = list_available_microphones()
        logger.debug(f"PyAudio microphones detected ({len(names)}): {names}")
    except Exception as e:
        print(f"[VOICE ERROR] {e}")
        logger.debug(f"Failed to list PyAudio microphones: {e}")
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    audio = None
    # Try PyAudio microphone
    try:
        print("[VOICE] Creating microphone")
        mic_init_start = time.perf_counter()
        mic = get_working_microphone()
        mic_init_end = time.perf_counter()
        print("[VOICE] Microphone created")
        print(f"[PERF] Mic init: {(mic_init_end - mic_init_start) * 1000:.0f} ms")
        with mic as source:
            print("[VOICE] Adjusting for ambient noise...")
            calib_start = time.perf_counter()
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            calib_end = time.perf_counter()
            print("[VOICE] Ambient calibration complete")
            print(f"[PERF] Ambient calibration: {(calib_end - calib_start) * 1000:.2f} ms")
            print("Listening using PyAudio...")
            print("[VOICE] Waiting for speech...")
            listen_start = time.perf_counter()
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            listen_end = time.perf_counter()
            print("[VOICE] Audio captured successfully")
            print("[WHISPER] Audio captured")
            print(f"[PERF] Listening: {(listen_end - listen_start) * 1000:.2f} ms")
    except Exception as e:
        print(f"[VOICE ERROR] {e}")
        logger.warning(f"PyAudio microphone failed ({e}); falling back to sounddevice.")
        # sounddevice device discovery counts as mic init
        mic_init_start = time.perf_counter()
        # record_via_sounddevice selects the device internally
        mic_init_end = time.perf_counter()
        print(f"[PERF] Mic init: {(mic_init_end - mic_init_start) * 1000:.0f} ms")
        listen_start = time.perf_counter()
        audio = record_via_sounddevice(duration=phrase_time_limit)
        listen_end = time.perf_counter()
        if audio is not None:
            print("[VOICE] Audio captured successfully")
            print("[WHISPER] Audio captured")
            print(f"[PERF] Listening: {(listen_end - listen_start) * 1000:.2f} ms")
    if audio is None:
        logger.warning("No audio captured from either PyAudio or sounddevice.")
        print("[VOICE] Returning transcript")
        print(f"[PERF] Total voice pipeline: {(time.perf_counter() - total_start) * 1000:.2f} ms")
        print("========== EXITING listen_for_command ==========")
        return None
    
    if _whisper_model is None:
        print("[WHISPER ERROR] Whisper model is not loaded")
        print("[VOICE] Returning transcript")
        print(f"[PERF] Total voice pipeline: {(time.perf_counter() - total_start) * 1000:.2f} ms")
        print("========== EXITING listen_for_command ==========")
        return None

    temp_wav_path = None
    try:
        print("[WHISPER] Transcribing...")
        # Save captured audio to temporary WAV file
        save_start = time.perf_counter()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav.write(audio.get_wav_data())
            temp_wav_path = temp_wav.name
        save_end = time.perf_counter()
        print(f"[PERF] Saving WAV: {(save_end - save_start) * 1000:.2f} ms")
        print(f"[PERF] WAV encode: {(save_end - save_start) * 1000:.0f} ms")

        # Transcribe the WAV file — CPU-optimised inference parameters:
        #   beam_size=1               greedy decoding; no beam search overhead
        #   condition_on_previous_text=False  skip cross-attention over prior tokens
        #   temperature=0             deterministic; disables fallback sampling loops
        #   vad_filter=False          our own VAD already trimmed the audio
        trans_start = time.perf_counter()
        segments, info = _whisper_model.transcribe(
            temp_wav_path,
            beam_size=1,
            condition_on_previous_text=False,
            temperature=0,
            vad_filter=False,
        )
        transcript = " ".join([segment.text for segment in segments])
        trans_end = time.perf_counter()
        print(f"[WHISPER] Transcript: {transcript}")
        print(f"[PERF] Whisper transcription: {(trans_end - trans_start) * 1000:.2f} ms")
        print(f"[PERF] Whisper: {(trans_end - trans_start) * 1000:.0f} ms")
        print("[VOICE] Returning transcript")
        print(f"[PERF] Total voice pipeline: {(time.perf_counter() - total_start) * 1000:.2f} ms")
        print("========== EXITING listen_for_command ==========")
        return transcript.strip()
    except Exception as e:
        print(f"[WHISPER ERROR] {e}")
        print("[VOICE] Returning transcript")
        print(f"[PERF] Total voice pipeline: {(time.perf_counter() - total_start) * 1000:.2f} ms")
        print("========== EXITING listen_for_command ==========")
        return None
    finally:
        # Delete temporary WAV file after transcription
        if temp_wav_path and os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
            except Exception as e_del:
                print(f"[WHISPER ERROR] Failed to delete temporary file: {e_del}")




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
            tts_init_start = time.perf_counter()
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
            tts_init_end = time.perf_counter()
            print(f"[PERF] TTS synthesis: {(tts_init_end - tts_init_start) * 1000:.0f} ms")

            playback_start = time.perf_counter()
            engine.runAndWait()
            playback_end = time.perf_counter()
            print(f"[PERF] Audio playback: {(playback_end - playback_start) * 1000:.0f} ms")
        except Exception as e:
            logger.error(f"Error in TTS speak: {e}")

    def listen(self, timeout: float = 6.0, phrase_time_limit: float = 10.0) -> str | None:
        """Listens using speech_recognition and transcribes via Google Cloud Speech API."""
        if not self.speech_enabled:
            print("Speech recognition is disabled. Ensure speechrecognition, sounddevice, and numpy are installed.")
            return None
        return listen_for_command(timeout=timeout, phrase_time_limit=phrase_time_limit)
