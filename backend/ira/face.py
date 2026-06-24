from __future__ import annotations

import base64
from dataclasses import dataclass


@dataclass(frozen=True)
class FaceRecognitionResult:
    recognized: bool
    faces: int
    message: str


class FaceRecognitionError(RuntimeError):
    pass


def detect_faces(image_base64: str) -> FaceRecognitionResult:
    image_bytes = _decode_base64_image(image_base64)

    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise FaceRecognitionError(
            "Local face detector is not installed. Run pip install -r requirements.txt in backend."
        ) from exc

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise FaceRecognitionError("Face image could not be decoded.")

    grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)
    if detector.empty():
        raise FaceRecognitionError("Local face detector model could not be loaded.")

    faces = detector.detectMultiScale(
        grayscale,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(40, 40),
    )
    face_count = len(faces)

    if face_count > 0:
        return FaceRecognitionResult(True, face_count, "USER RECOGNIZED")

    return FaceRecognitionResult(False, 0, "SEARCHING FACE")


def _decode_base64_image(image_base64: str) -> bytes:
    value = image_base64.strip()

    if not value:
        raise FaceRecognitionError("No face image was provided.")

    if "," in value and value.startswith("data:image/"):
        value = value.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(value, validate=True)
    except ValueError as exc:
        raise FaceRecognitionError("Face image must be valid base64.") from exc

    if not image_bytes:
        raise FaceRecognitionError("No face image was provided.")

    return image_bytes
