from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import google_api_key

VISION_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"


@dataclass(frozen=True)
class FaceRecognitionResult:
    recognized: bool
    faces: int
    message: str


class FaceRecognitionError(RuntimeError):
    pass


def detect_faces(image_base64: str) -> FaceRecognitionResult:
    api_key = google_api_key()

    if not api_key:
        raise FaceRecognitionError("Google API key is not configured.")

    clean_image = _clean_base64_image(image_base64)
    payload = {
        "requests": [
            {
                "image": {"content": clean_image},
                "features": [{"type": "FACE_DETECTION", "maxResults": 4}],
            }
        ]
    }

    request = Request(
        f"{VISION_ENDPOINT}?key={api_key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=12) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise FaceRecognitionError(_google_error_message(details)) from exc
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise FaceRecognitionError("Google Vision face scan failed.") from exc

    return _parse_vision_response(body)


def _google_error_message(details: str) -> str:
    try:
        payload = json.loads(details)
    except json.JSONDecodeError:
        return "Google Vision rejected the face scan."

    error = payload.get("error", {})
    message = str(error.get("message", "Google Vision rejected the face scan."))
    details = error.get("details", [])

    if any(detail.get("reason") == "BILLING_DISABLED" for detail in details if isinstance(detail, dict)):
        return "Google Cloud billing is disabled for this project."

    if error.get("status") == "PERMISSION_DENIED" and "billing" in message.lower():
        return "Google Cloud billing is disabled for this project."

    if "Cloud Vision API has not been used" in message or "disabled" in message.lower():
        return "Cloud Vision API is disabled for this Google project."

    if error.get("status") == "PERMISSION_DENIED":
        return "Google Vision permission denied for this API key."

    return message


def _clean_base64_image(image_base64: str) -> str:
    value = image_base64.strip()

    if not value:
        raise FaceRecognitionError("No face image was provided.")

    if "," in value and value.startswith("data:image/"):
        value = value.split(",", 1)[1]

    try:
        base64.b64decode(value, validate=True)
    except ValueError as exc:
        raise FaceRecognitionError("Face image must be valid base64.") from exc

    return value


def _parse_vision_response(body: dict[str, Any]) -> FaceRecognitionResult:
    responses = body.get("responses", [])

    if not responses:
        raise FaceRecognitionError("Google Vision returned no response.")

    first_response = responses[0]

    if "error" in first_response:
        message = str(first_response["error"].get("message", "Face scan failed."))
        raise FaceRecognitionError(message)

    faces = first_response.get("faceAnnotations", [])
    face_count = len(faces)

    if face_count > 0:
        return FaceRecognitionResult(True, face_count, "USER RECOGNIZED")

    return FaceRecognitionResult(False, 0, "SEARCHING FACE")
