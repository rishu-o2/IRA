from __future__ import annotations

import base64
import sys
from types import SimpleNamespace

import pytest

from ira.face import FaceRecognitionError, detect_faces


class FakeCascadeClassifier:
    faces: list[tuple[int, int, int, int]] = []

    def __init__(self, path: str) -> None:
        self.path = path

    def empty(self) -> bool:
        return False

    def detectMultiScale(self, image: object, **kwargs: object) -> list[tuple[int, int, int, int]]:
        return self.faces


def install_fake_cv2(monkeypatch: pytest.MonkeyPatch, faces: list[tuple[int, int, int, int]]) -> None:
    FakeCascadeClassifier.faces = faces
    fake_cv2 = SimpleNamespace(
        IMREAD_COLOR=1,
        COLOR_BGR2GRAY=6,
        CascadeClassifier=FakeCascadeClassifier,
        data=SimpleNamespace(haarcascades="C:/opencv/haarcascades/"),
        cvtColor=lambda frame, code: "gray-frame",
        imdecode=lambda image_array, mode: "decoded-frame",
    )
    fake_np = SimpleNamespace(uint8="uint8", frombuffer=lambda image_bytes, dtype: image_bytes)

    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.setitem(sys.modules, "numpy", fake_np)


def test_detect_faces_uses_local_detector(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_cv2(monkeypatch, [(10, 10, 80, 80)])

    image = base64.b64encode(b"fake-image").decode("utf-8")
    result = detect_faces(f"data:image/jpeg;base64,{image}")

    assert result.recognized is True
    assert result.faces == 1
    assert result.message == "USER RECOGNIZED"


def test_detect_faces_reports_no_local_face(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_cv2(monkeypatch, [])

    image = base64.b64encode(b"fake-image").decode("utf-8")
    result = detect_faces(image)

    assert result.recognized is False
    assert result.faces == 0
    assert result.message == "SEARCHING FACE"


def test_detect_faces_rejects_invalid_base64() -> None:
    with pytest.raises(FaceRecognitionError, match="valid base64"):
        detect_faces("not-base64")


def test_detect_faces_requires_local_detector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "cv2", None)
    monkeypatch.setitem(sys.modules, "numpy", None)

    image = base64.b64encode(b"fake-image").decode("utf-8")

    with pytest.raises(FaceRecognitionError, match="Local face detector is not installed"):
        detect_faces(image)
