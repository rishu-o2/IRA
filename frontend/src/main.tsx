import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { IraAvatar3D } from "./IraAvatar3D";
import "./styles.css";

type FaceDetectorConstructor = new (options?: { fastMode?: boolean; maxDetectedFaces?: number }) => FaceDetector;

type FaceDetector = {
  detect: (source: CanvasImageSource) => Promise<unknown[]>;
};

declare global {
  interface Window {
    FaceDetector?: FaceDetectorConstructor;
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

function App() {
  const [status, setStatus] = useState("IRA ONLINE");
  const [faceStatus, setFaceStatus] = useState("FACE ID STARTING");
  const [isFaceScanning, setIsFaceScanning] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const autoStartedRef = useRef(false);
  const faceScanInFlightRef = useRef(false);
  const faceScanTimerRef = useRef<number | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    const loadVoices = () => {
      setVoices(window.speechSynthesis.getVoices());
    };

    loadVoices();
    window.speechSynthesis.addEventListener("voiceschanged", loadVoices);

    return () => {
      window.speechSynthesis.removeEventListener("voiceschanged", loadVoices);
      window.speechSynthesis.cancel();
      stopFaceRecognition();
    };
  }, []);

  useEffect(() => {
    if (autoStartedRef.current) {
      return;
    }

    autoStartedRef.current = true;
    startFaceRecognition();
  }, []);

  function stopFaceRecognition() {
    if (faceScanTimerRef.current !== null) {
      window.clearInterval(faceScanTimerRef.current);
      faceScanTimerRef.current = null;
    }

    const stream = videoRef.current?.srcObject;
    if (stream instanceof MediaStream) {
      stream.getTracks().forEach((track) => track.stop());
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setIsFaceScanning(false);
  }

  function speak(text: string) {
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = pickFemaleVoice(voices.length > 0 ? voices : window.speechSynthesis.getVoices());
    utterance.pitch = 1.12;
    utterance.rate = 0.94;
    utterance.volume = 1;
    utterance.onstart = () => {
      setIsSpeaking(true);
      setStatus("IRA SPEAKING");
    };
    utterance.onend = () => {
      setIsSpeaking(false);
      setStatus("IRA ONLINE");
    };

    window.speechSynthesis.speak(utterance);
  }

async function startFaceRecognition() {
    if (isFaceScanning) {
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 640 },
          height: { ideal: 480 }
        },
        audio: false
      });

      if (!videoRef.current) {
        return;
      }

      videoRef.current.srcObject = stream;
      await videoRef.current.play();

      const detector = window.FaceDetector ? new window.FaceDetector({ fastMode: true, maxDetectedFaces: 1 }) : null;
      setIsFaceScanning(true);
      setFaceStatus("GOOGLE FACE SCAN");
      setStatus("FACE RECOGNITION ACTIVE");

      faceScanTimerRef.current = window.setInterval(async () => {
        if (!videoRef.current || videoRef.current.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
          return;
        }

        if (faceScanInFlightRef.current) {
          return;
        }

        faceScanInFlightRef.current = true;

        try {
          const result = await scanFaceWithBackend(videoRef.current);

          if (result.recognized) {
            setFaceStatus("USER RECOGNIZED");
            setStatus("ACCESS CONFIRMED");
            speak("Face recognized. Welcome back.");
            stopFaceRecognition();
          } else {
            setFaceStatus("SEARCHING FACE");
          }
        } catch (error) {
          const message = error instanceof Error ? error.message : "";

          if (message.includes("Cloud Vision API is disabled")) {
            setFaceStatus("VISION API DISABLED");
            setStatus("ENABLE GOOGLE VISION");
            stopFaceRecognition();
            return;
          }

          if (message.includes("permission denied")) {
            setFaceStatus("VISION PERMISSION DENIED");
            setStatus("CHECK GOOGLE API KEY");
            stopFaceRecognition();
            return;
          }

          if (message.includes("billing is disabled")) {
            setFaceStatus("BILLING DISABLED");
            setStatus("ENABLE GOOGLE BILLING");
            stopFaceRecognition();
            return;
          }

          try {
            if (!detector || !videoRef.current) {
              setFaceStatus("BACKEND OFFLINE");
              return;
            }

            const faces = await detector.detect(videoRef.current);

            if (faces.length > 0) {
              setFaceStatus("USER RECOGNIZED");
              setStatus("ACCESS CONFIRMED");
              speak("Face recognized. Welcome back.");
              stopFaceRecognition();
            } else {
              setFaceStatus("SEARCHING FACE");
            }
          } catch {
            setFaceStatus("FACE SCAN ERROR");
            stopFaceRecognition();
          }
        } finally {
          faceScanInFlightRef.current = false;
        }
      }, 2200);
    } catch {
      setFaceStatus("CAMERA BLOCKED");
      setStatus("CAMERA PERMISSION NEEDED");
      speak("Camera access is blocked. Please allow camera permission for face recognition.");
      stopFaceRecognition();
    }
  }

  async function scanFaceWithBackend(video: HTMLVideoElement) {
    const image = captureVideoFrame(video);
    const response = await fetch("http://127.0.0.1:8765/face-recognition", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ image })
    });

    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as { error?: string } | null;
      throw new Error(payload?.error ?? "Face backend request failed");
    }

    return (await response.json()) as { recognized: boolean; faces: number; text: string };
  }

  function captureVideoFrame(video: HTMLVideoElement) {
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Unable to capture camera frame");
    }

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.72);
  }

  return (
    <main className="app-shell" aria-label="IRA voice hologram">
      <div className="ira-brand" aria-label="IRA full form">
        <strong>IRA</strong>
        <span>INTELLIGENT RESPONSIVE ASSISTANT</span>
      </div>
      <section
        className={`ira-stage ${isSpeaking ? "is-speaking" : ""} ${isFaceScanning ? "is-face-scanning" : ""}`}
      >
        <IraAvatar3D />
        <video ref={videoRef} className="face-video" playsInline muted aria-hidden="true" />
        <div className="voice-core" aria-live="polite" aria-label="IRA status">
          <span className="voice-status">{status}</span>
          <span className="face-status">{faceStatus}</span>
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
