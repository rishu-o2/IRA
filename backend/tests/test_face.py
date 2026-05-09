from __future__ import annotations

import base64
import json

import pytest

from ira import face
from ira.face import FaceRecognitionError, detect_faces


class DummyResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "DummyResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_detect_faces_uses_google_vision_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request: object, timeout: int) -> DummyResponse:
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return DummyResponse({"responses": [{"faceAnnotations": [{"joyLikelihood": "VERY_UNLIKELY"}]}]})

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr(face, "urlopen", fake_urlopen)

    image = base64.b64encode(b"fake-image").decode("utf-8")
    result = detect_faces(image)

    assert result.recognized is True
    assert result.faces == 1
    assert "key=test-key" in str(captured["url"])
    assert captured["timeout"] == 12
    assert captured["body"] == {
        "requests": [
            {
                "image": {"content": image},
                "features": [{"type": "FACE_DETECTION", "maxResults": 4}],
            }
        ]
    }


def test_detect_faces_rejects_invalid_base64(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    with pytest.raises(FaceRecognitionError, match="valid base64"):
        detect_faces("not-base64")
