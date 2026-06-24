import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { IraAvatar3D } from "./IraAvatar3D";
import "./styles.css";

type FaceDetectorConstructor = new (options?: { fastMode?: boolean; maxDetectedFaces?: number }) => FaceDetector;

type FaceDetector = {
  detect: (source: CanvasImageSource) => Promise<unknown[]>;
};

type SpeechRecognitionConstructor = new () => SpeechRecognition;

type SpeechRecognition = EventTarget & {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onstart: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionEvent = {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      isFinal: boolean;
      [index: number]: {
        transcript: string;
      };
    };
  };
};

type BackendFaceResult = {
  ok?: boolean;
  recognized?: boolean;
  faces?: number;
  message?: string;
  error?: string;
};

type DesktopSpeechEvent = {
  type: "status" | "transcript" | "error";
  status?: string;
  text?: string;
  confidence?: number;
  error?: string;
};

declare global {
  interface Window {
    FaceDetector?: FaceDetectorConstructor;
    iraDesktop?: {
      platform: string;
      nativeSpeechSupported: () => Promise<boolean>;
      onSpeechEvent: (callback: (event: DesktopSpeechEvent) => void) => () => void;
      showWindow: () => Promise<void>;
    };
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitAudioContext?: typeof AudioContext;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

const femaleVoiceNames = [
  "zira",
  "susan",
  "hazel",
  "samantha",
  "victoria",
  "karen",
  "moira",
  "tessa",
  "veena",
  "female",
  "woman",
  "google us english"
];

function pickFemaleVoice(voices: SpeechSynthesisVoice[]) {
  return (
    voices.find((voice) => femaleVoiceNames.some((name) => voice.name.toLowerCase().includes(name))) ??
    voices.find((voice) => voice.lang.toLowerCase().startsWith("en")) ??
    voices[0] ??
    null
  );
}

function cleanVoiceCommand(transcript: string) {
  return transcript
    .trim()
    .replace(/[.!?]+$/g, "")
    .replace(/^\s*(hey|hello|hi)\s*,?\s+ira\b[:,]?\s*/i, "")
    .replace(/^\s*(open|wake|activate)\s+(?:my\s+)?(ira|laptop|computer)\b[:,]?\s*/i, "")
    .replace(/^\s*ira\b[:,]?\s*/i, "")
    .replace(/^\s*(please|can you|could you|would you)\s+/i, "")
    .trim();
}

function isWakePhrase(transcript: string) {
  return /^\s*(?:(hey|hello|hi)\s*,?\s+ira|open\s+(?:my\s+)?(?:ira|laptop|computer)|wake\s+(?:my\s+)?(?:ira|laptop|computer)|activate\s+(?:my\s+)?(?:ira|laptop|computer))\b/i.test(transcript.trim());
}

function getBackendURL(): string {
  const host = window.location.hostname;

  if (host && host !== "localhost") {
    return `http://${host}:8765`;
  }

  return "http://127.0.0.1:8765";
}

function App() {
  const [status, setStatus] = useState("IRA ONLINE");
  const [faceStatus, setFaceStatusState] = useState("FACE ID STARTING");
  const [voiceStatus, setVoiceStatus] = useState("VOICE STARTING");
  const [lastHeard, setLastHeard] = useState("");
  const [typedCommand, setTypedCommand] = useState("");
  const [isFaceScanning, setIsFaceScanning] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isVoiceListening, setIsVoiceListening] = useState(false);
  const [gestureMode, setGestureMode] = useState(false);
  const [gestureStatus, setGestureStatus] = useState("GESTURE INACTIVE");
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const autoStartedRef = useRef(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioLevelTimerRef = useRef<number | null>(null);
  const faceScanTimerRef = useRef<number | null>(null);
  const faceStatusRef = useRef("FACE ID STARTING");
  const hasWelcomedFaceRef = useRef(false);
  const micStreamRef = useRef<MediaStream | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const shouldListenRef = useRef(true);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const faceDetectorRef = useRef<FaceDetector | null>(null);
  const backendFaceDisabledRef = useRef(false);
  const cameraStartingRef = useRef(false);
  const voiceRestartTimerRef = useRef<number | null>(null);
  const voiceErrorCountRef = useRef(0);
  const backendURLRef = useRef(getBackendURL());
  const cameraRetryTimerRef = useRef<number | null>(null);
  const cameraRetryCountRef = useRef(0);

  function setFaceStatus(value: string) {
    faceStatusRef.current = value;
    setFaceStatusState(value);
  }

  useEffect(() => {
    shouldListenRef.current = true;

    const loadVoices = () => {
      setVoices(window.speechSynthesis.getVoices());
    };

    const stopNativeSpeechEvents = window.iraDesktop?.onSpeechEvent?.((event) => {
      if (event.type === "status") {
        setVoiceStatus(event.status || "NATIVE LISTENING");
        setStatus("VOICE ONLINE");
        setIsVoiceListening(true);
        return;
      }

      if (event.type === "error") {
        setVoiceStatus("NATIVE VOICE ERROR");
        setStatus("CHECK MICROPHONE");
        if (event.error) {
          setLastHeard(event.error);
        }
        return;
      }

      if (event.type === "transcript" && event.text?.trim()) {
        const transcript = event.text.trim();
        setLastHeard(transcript);
        setVoiceStatus("HEARD YOU");
        setStatus("PROCESSING VOICE");
        void handleVoiceCommand(transcript);
      }
    });

    loadVoices();
    window.speechSynthesis.addEventListener("voiceschanged", loadVoices);

    return () => {
      shouldListenRef.current = false;
      autoStartedRef.current = false;
      stopNativeSpeechEvents?.();
      window.speechSynthesis.removeEventListener("voiceschanged", loadVoices);
      window.speechSynthesis.cancel();
      micStreamRef.current?.getTracks().forEach((track) => track.stop());
      recognitionRef.current?.stop();
      stopMicLevelMonitor();
      stopFaceRecognition();
      
      // Clean up any pending timers
      if (voiceRestartTimerRef.current !== null) {
        window.clearTimeout(voiceRestartTimerRef.current);
      }
      if (cameraRetryTimerRef.current !== null) {
        window.clearTimeout(cameraRetryTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    shouldListenRef.current = true;

    if (autoStartedRef.current) {
      return;
    }

    autoStartedRef.current = true;
    startFaceRecognition();

    if (window.iraDesktop?.platform === "win32") {
      setVoiceStatus("NATIVE VOICE STARTING");
      setStatus("VOICE ONLINE");
      setIsVoiceListening(true);
      return;
    }

    startVoiceSystem();
  }, []);

  async function startVoiceSystem() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = stream;
      startMicLevelMonitor(stream);
      window.setTimeout(() => startVoiceRecognition(), 350);
    } catch (error) {
      const errorName = error instanceof DOMException ? error.name : "Unknown";
      if (errorName === "NotFoundError") {
        setVoiceStatus("NO MIC DETECTED");
        setStatus("CHECK MICROPHONE");
        return;
      }

      if (errorName === "NotReadableError") {
        setVoiceStatus("MIC BUSY");
        setStatus("CLOSE OTHER MIC APPS");
        return;
      }

      setVoiceStatus(`MIC ERROR: ${errorName}`);
      setStatus("ALLOW MICROPHONE");
    }
  }

  function stopMicLevelMonitor() {
    if (audioLevelTimerRef.current !== null) {
      window.clearInterval(audioLevelTimerRef.current);
      audioLevelTimerRef.current = null;
    }

    void audioContextRef.current?.close();
    audioContextRef.current = null;
  }

  function startMicLevelMonitor(stream: MediaStream) {
    stopMicLevelMonitor();

    const AudioContextConstructor = window.AudioContext ?? window.webkitAudioContext;
    if (!AudioContextConstructor) {
      setVoiceStatus("MIC ONLINE");
      return;
    }

    const audioContext = new AudioContextConstructor();
    const analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(stream);
    const samples = new Uint8Array(analyser.frequencyBinCount);

    analyser.fftSize = 256;
    source.connect(analyser);
    audioContextRef.current = audioContext;

    setVoiceStatus("MIC ONLINE");
    audioLevelTimerRef.current = window.setInterval(() => {
      analyser.getByteFrequencyData(samples);
      const peak = samples.reduce((max, sample) => Math.max(max, sample), 0);

      if (peak > 18 && !recognitionRef.current && !window.speechSynthesis.speaking) {
        setVoiceStatus("MIC HEARS AUDIO");
      }
    }, 700);
  }

  function stopFaceRecognition(options: { clearRetryTimer?: boolean; resetRetryCount?: boolean } = {}) {
    const { clearRetryTimer = true, resetRetryCount = true } = options;

    if (faceScanTimerRef.current !== null) {
      window.clearInterval(faceScanTimerRef.current);
      faceScanTimerRef.current = null;
    }

    if (clearRetryTimer && cameraRetryTimerRef.current !== null) {
      window.clearTimeout(cameraRetryTimerRef.current);
      cameraRetryTimerRef.current = null;
    }

    const stream = videoRef.current?.srcObject;
    if (stream instanceof MediaStream) {
      stream.getTracks().forEach((track) => track.stop());
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    faceDetectorRef.current = null;
    cameraStartingRef.current = false;
    if (resetRetryCount) {
      cameraRetryCountRef.current = 0;
    }
    setIsFaceScanning(false);
  }

  function speak(text: string) {
    recognitionRef.current?.stop();
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = pickFemaleVoice(voices.length > 0 ? voices : window.speechSynthesis.getVoices());
    utterance.pitch = 1.12;
    utterance.rate = 0.94;
    utterance.volume = 1;
    utterance.onstart = () => {
      setIsSpeaking(true);
      setStatus("IRA SPEAKING");
      setVoiceStatus("REPLYING");
    };
    utterance.onend = () => {
      setIsSpeaking(false);
      setStatus("IRA ONLINE");
      if (shouldListenRef.current) {
        window.setTimeout(() => startVoiceRecognition(), 450);
      }
    };

    window.speechSynthesis.speak(utterance);
  }

  function startVoiceRecognition() {
    const Recognition = window.SpeechRecognition ?? window.webkitSpeechRecognition;

    if (!Recognition) {
      setIsVoiceListening(false);
      setVoiceStatus("SPEECH RECOGNITION MISSING");
      setStatus("TYPE COMMANDS FOR NOW");
      return;
    }

    // Clear any pending restart timers
    if (voiceRestartTimerRef.current !== null) {
      window.clearTimeout(voiceRestartTimerRef.current);
      voiceRestartTimerRef.current = null;
    }

    if (recognitionRef.current || window.speechSynthesis.speaking) {
      return;
    }

    let recognition: SpeechRecognition;
    try {
      recognition = new Recognition();
    } catch {
      setIsVoiceListening(false);
      setVoiceStatus("SPEECH START FAILED");
      setStatus("TYPE COMMANDS FOR NOW");
      return;
    }
    recognitionRef.current = recognition;
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.maxAlternatives = 1;

    let hasDetectedSpeech = false;

    recognition.onstart = () => {
      voiceErrorCountRef.current = 0;
      setIsVoiceListening(true);
      setVoiceStatus("LISTENING");
      setStatus("VOICE ONLINE");
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let transcript = "";

      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        transcript += event.results[index][0].transcript;
      }

      const heard = transcript.trim();
      if (heard) {
        hasDetectedSpeech = true;
        setLastHeard(heard);
        setVoiceStatus("HEARD YOU");
      }

      const lastResult = event.results[event.results.length - 1];
      if (lastResult?.isFinal && heard) {
        recognition.stop();
        handleVoiceCommand(heard);
      }
    };

    recognition.onerror = (event: { error: string }) => {
      recognitionRef.current = null;
      setIsVoiceListening(false);
      const errorType = event.error;

      if (errorType === "not-allowed") {
        setVoiceStatus("MIC PERMISSION NEEDED");
        setStatus("ALLOW MICROPHONE");
        return;
      }

      if (errorType === "audio-capture" || errorType === "no-microphone") {
        setVoiceStatus("NO MIC DETECTED");
        if (shouldListenRef.current) {
          voiceRestartTimerRef.current = window.setTimeout(() => startVoiceRecognition(), 3000);
        }
        return;
      }

      if (errorType === "no-speech" || errorType === "timeout") {
        voiceErrorCountRef.current += 1;
        
        // If we had many consecutive no-speech errors, give it more time
        const delayMs = voiceErrorCountRef.current > 2 ? 2000 : 1200;
        
        setVoiceStatus("LISTENING (NO SPEECH YET)");
        if (shouldListenRef.current) {
          voiceRestartTimerRef.current = window.setTimeout(() => startVoiceRecognition(), delayMs);
        }
        return;
      }

      if (errorType === "network" || errorType === "service-unavailable") {
        voiceErrorCountRef.current += 1;
        const delayMs = Math.min(1000 * voiceErrorCountRef.current, 5000);
        
        setVoiceStatus("SPEECH SERVICE RETRYING");
        if (shouldListenRef.current) {
          voiceRestartTimerRef.current = window.setTimeout(() => startVoiceRecognition(), delayMs);
        }
        return;
      }

      setVoiceStatus(`VOICE ERROR: ${errorType}`);
      if (shouldListenRef.current) {
        voiceRestartTimerRef.current = window.setTimeout(() => startVoiceRecognition(), 2000);
      }
    };

    recognition.onend = () => {
      recognitionRef.current = null;
      setIsVoiceListening(false);

      // Only auto-restart if we're supposed to listen and synthesis isn't active
      if (shouldListenRef.current && !window.speechSynthesis.speaking) {
        // Give a small delay before restarting to avoid immediate restart loop
        voiceRestartTimerRef.current = window.setTimeout(() => startVoiceRecognition(), 500);
      }
    };

    setIsVoiceListening(true);
    setVoiceStatus("LISTENING");
    setStatus("VOICE ONLINE");
    try {
      recognition.start();
    } catch {
      recognitionRef.current = null;
      setIsVoiceListening(false);
      setVoiceStatus("SPEECH START FAILED");
      setStatus("TYPE COMMANDS FOR NOW");
    }
  }

  async function handleVoiceCommand(transcript: string) {
    const wake = isWakePhrase(transcript);
    if (wake) {
      await window.iraDesktop?.showWindow();
    }

    const command = cleanVoiceCommand(transcript);
    if (!command) {
      if (wake) {
        speak("Hello sir. I am awake and ready.");
        return;
      }
      speak("Yes. I am here.");
      return;
    }

    await runAssistantCommand(command);
  }

  async function submitTypedCommand(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const command = typedCommand.trim();
    if (!command) {
      return;
    }

    setTypedCommand("");
    setLastHeard(command);
    await runAssistantCommand(command);
  }

  async function runAssistantCommand(command: string) {
    const normalizedCommand = cleanVoiceCommand(command);
    const lowered = normalizedCommand.toLowerCase();

    if (lowered.includes("gesture mode") || lowered.includes("gesture control") || lowered.includes("hand gesture") || lowered.includes("hand gestures")) {
      const disable = lowered.includes("stop") || lowered.includes("turn off") || lowered.includes("disable") || lowered.includes("off");
      if (disable) {
        setGestureMode(false);
        setGestureStatus("GESTURE INACTIVE");
        speak("Gesture mode disabled. I will stop moving with hand motion.");
        return;
      }

      setGestureMode(true);
      setGestureStatus("GESTURE ACTIVE");
      speak("Gesture mode enabled. Move your hand in front of the camera to guide me like Dr. Strange.");
      return;
    }

    if (!normalizedCommand || lowered === "ira") {
      speak("Yes. I am here.");
      return;
    }

    if (lowered.includes("can you see me") || lowered.includes("do you see me") || lowered.includes("see me")) {
      speak(faceVisibilityReply());
      return;
    }

    try {
      setStatus("EXECUTING COMMAND");
      setVoiceStatus("PROCESSING");
      const response = await sendCommandToBackend(normalizedCommand);
      speak(response);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Backend not connected.";
      speak(`Backend request failed. ${message}`);
    }
  }

  function faceVisibilityReply() {
    const currentFaceStatus = faceStatusRef.current;

    if (currentFaceStatus === "USER RECOGNIZED") {
      return "Yes. I can see your face.";
    }

    if (currentFaceStatus === "SEARCHING FACE") {
      return "My camera is active, but I have not clearly detected your face yet.";
    }

    if (currentFaceStatus === "CAMERA ACTIVE") {
      return "The camera is active. Your browser does not support local face detection, so I can access the camera but cannot confirm a face.";
    }

    if (currentFaceStatus === "CAMERA BLOCKED") {
      return "I cannot see you because camera permission is blocked.";
    }

    return "I am still starting the camera scan.";
  }

  async function sendJsonToBackend<TPayload extends object, TResult>(
    endpoint: string,
    payload: TPayload,
    timeoutMs = 2200
  ) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
    const requestURL = `${backendURLRef.current}${endpoint}`;

    try {
      const response = await fetch(requestURL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      if (!response.ok) {
        const details = await response.text().catch(() => "");
        throw new Error(`${endpoint} returned ${response.status}${details ? `: ${details}` : ""}`);
      }

      return (await response.json()) as TResult;
    } catch (error) {
      const reason = error instanceof Error ? error.message : "failed";
      throw new Error(`Unified backend ${backendURLRef.current}${endpoint} failed: ${reason}`);
    } finally {
      window.clearTimeout(timeout);
    }
  }

  async function sendCommandToBackend(command: string) {
    const payload = await sendJsonToBackend<{ message: string }, { text?: string }>("/command", { message: command });
    return payload.text ?? "Command completed.";
  }

  function captureFaceFrame() {
    const video = videoRef.current;

    if (!video || video.videoWidth === 0 || video.videoHeight === 0) {
      return null;
    }

    const canvas = document.createElement("canvas");
    const maxWidth = 480;
    const scale = Math.min(1, maxWidth / video.videoWidth);
    canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
    canvas.height = Math.max(1, Math.round(video.videoHeight * scale));

    const context = canvas.getContext("2d");
    if (!context) {
      return null;
    }

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.72);
  }

  async function scanFaceWithBackend() {
    if (backendFaceDisabledRef.current) {
      return null;
    }

    const image = captureFaceFrame();
    if (!image) {
      return null;
    }

    try {
      const result = await sendJsonToBackend<{ image: string }, BackendFaceResult>("/face", { image }, 6500);
      return result;
    } catch (error) {
      const message = error instanceof Error ? error.message : "";

      if (
        message.includes("Local face detector is not installed") ||
        message.includes("Local face detector model could not be loaded")
      ) {
        backendFaceDisabledRef.current = true;
      }

      return null;
    }
  }

  async function startFaceRecognition() {
    if (isFaceScanning || cameraStartingRef.current) {
      return;
    }

    if (cameraRetryTimerRef.current !== null) {
      window.clearTimeout(cameraRetryTimerRef.current);
      cameraRetryTimerRef.current = null;
    }

    cameraStartingRef.current = true;

    try {
      const existingStream = videoRef.current?.srcObject;
      if (existingStream instanceof MediaStream) {
        existingStream.getTracks().forEach((track) => track.stop());
        if (videoRef.current) {
          videoRef.current.srcObject = null;
        }
      }

      setFaceStatus("REQUESTING CAMERA ACCESS");
      setStatus("CAMERA STARTING");
      console.log("[IRA] Requesting camera access...");

      const constraints = {
        video: true,
        audio: false
      };

      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia(constraints);
      } catch (innerError) {
        console.warn("[IRA] Initial camera request failed, retrying with simple constraints.", innerError);
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      }

      if (!videoRef.current) {
        throw new Error("Video element is not mounted");
      }

      videoRef.current.srcObject = stream;
      await videoRef.current.play();

      cameraRetryCountRef.current = 0;
      faceDetectorRef.current = window.FaceDetector ? new window.FaceDetector({ fastMode: true, maxDetectedFaces: 1 }) : null;
      setIsFaceScanning(true);
      setFaceStatus("BACKEND FACE SCAN");
      setStatus("FACE RECOGNITION ACTIVE");
      console.log("[IRA] Camera stream started successfully.");

      faceScanTimerRef.current = window.setInterval(async () => {
        if (!videoRef.current || videoRef.current.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
          return;
        }

        try {
          const backendFace = await scanFaceWithBackend();

          if (backendFace?.ok) {
            if (backendFace.recognized || (backendFace.faces ?? 0) > 0) {
              setFaceStatus(backendFace.message || "USER RECOGNIZED");
              setStatus("ACCESS CONFIRMED");
              if (!hasWelcomedFaceRef.current) {
                hasWelcomedFaceRef.current = true;
                speak("I can see you. Face recognized.");
              }
              return;
            }

            setFaceStatus(backendFace.message || "SEARCHING FACE");
            return;
          }

          if (!faceDetectorRef.current) {
            setFaceStatus("CAMERA ACTIVE");
            return;
          }

          const faces = await faceDetectorRef.current.detect(videoRef.current);

          if (faces.length > 0) {
            setFaceStatus("USER RECOGNIZED");
            setStatus("ACCESS CONFIRMED");
            if (!hasWelcomedFaceRef.current) {
              hasWelcomedFaceRef.current = true;
              speak("I can see you. Face recognized.");
            }
            return;
          }

          setFaceStatus("SEARCHING FACE");
        } catch (detectorError) {
          console.error("[IRA] Face detector error:", detectorError);
          setFaceStatus("CAMERA ACTIVE");
          setStatus("FACE RECOGNITION ACTIVE");
        }
      }, 1800);
    } catch (error) {
      const err = error as any;
      const errorName = err?.name || "Unknown";
      const errorMessage = err?.message || String(err);
      console.error("[IRA] Camera access error:", errorName, errorMessage);
      setFaceStatus(`CAMERA ERROR: ${errorName}`);

      cameraRetryCountRef.current += 1;
      const maxRetries = 5;
      const delay = Math.min(2000 * cameraRetryCountRef.current, 10000);

      if (errorName === "NotAllowedError" || errorName === "SecurityError") {
        setStatus("CAMERA PERMISSION DENIED");
        speak("Camera access is blocked. Please allow camera permission in your system settings.");
      } else if (errorName === "NotFoundError") {
        setStatus("NO CAMERA DEVICE");
        speak("No camera device found on your computer.");
      } else if (errorName === "NotReadableError") {
        setStatus("CAMERA BUSY");
        setFaceStatus("CAMERA BUSY");
        if (cameraRetryCountRef.current <= maxRetries) {
          cameraRetryTimerRef.current = window.setTimeout(() => startFaceRecognition(), delay);
        } else {
          speak("The camera is busy or locked. Close any other camera apps and reload IRA.");
        }
      } else {
        if (cameraRetryCountRef.current <= maxRetries) {
          setStatus("CAMERA RETRYING");
          cameraRetryTimerRef.current = window.setTimeout(() => startFaceRecognition(), delay);
        } else {
          setStatus("CAMERA ERROR");
          speak("Camera access failed. Please check your camera settings and restart the app.");
        }
      }

      stopFaceRecognition({ clearRetryTimer: false, resetRetryCount: false });
    } finally {
      cameraStartingRef.current = false;
    }
  }

  return (
    <main className="app-shell" aria-label="IRA voice hologram">
      <div className="ira-brand" aria-label="IRA full form">
        <strong>IRA</strong>
        <span>INTELLIGENT RESPONSIVE ASSISTANT</span>
      </div>
      <section
        className={`ira-stage ${isVoiceListening ? "is-listening" : ""} ${isSpeaking ? "is-speaking" : ""} ${
          isFaceScanning ? "is-face-scanning" : ""
        }`}
      >
        <IraAvatar3D gestureEnabled={gestureMode} gestureSource={videoRef.current} />
        <video ref={videoRef} className="face-video" playsInline muted aria-hidden="true" />
        <div className="voice-core" aria-live="polite" aria-label="IRA status">
          <span className="voice-status">{status}</span>
          <span className="face-status">{voiceStatus}</span>
          <span className="face-status">{faceStatus}</span>
          <span className="face-status">{gestureStatus}</span>
          {lastHeard ? <span className="voice-transcript">{lastHeard}</span> : null}
        </div>
      </section>
      <form className="command-bar" onSubmit={submitTypedCommand}>
        <input
          aria-label="Type an IRA command"
          placeholder="Type a command..."
          value={typedCommand}
          onChange={(event) => setTypedCommand(event.target.value)}
        />
        <button type="submit">Send</button>
      </form>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
