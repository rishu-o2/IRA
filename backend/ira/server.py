from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .assistant import IRAAssistant
from .face import FaceRecognitionError, detect_faces

HOST = "127.0.0.1"
PORT = 8765


class IRARequestHandler(BaseHTTPRequestHandler):
    assistant = IRAAssistant()

    def do_OPTIONS(self) -> None:
        self._send_empty(204)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json({"ok": True, "name": "IRA"})
            return

        self._send_json({"ok": False, "error": "Not found"}, status=404)

    def do_POST(self) -> None:
        if self.path == "/command":
            self._handle_command()
            return

        if self.path == "/face-recognition":
            self._handle_face_recognition()
            return

        self._send_json({"ok": False, "error": "Not found"}, status=404)

    def _handle_command(self) -> None:
        try:
            payload = self._read_json()
            message = str(payload.get("message", "")).strip()
            response = self.assistant.handle(message)
        except json.JSONDecodeError:
            self._send_json({"ok": False, "error": "Invalid JSON"}, status=400)
            return

        self._send_json(
            {
                "ok": response.handled,
                "text": response.text,
                "handled": response.handled,
            }
        )

    def _handle_face_recognition(self) -> None:
        try:
            payload = self._read_json()
            image = str(payload.get("image", "")).strip()
            result = detect_faces(image)
        except json.JSONDecodeError:
            self._send_json({"ok": False, "error": "Invalid JSON"}, status=400)
            return
        except FaceRecognitionError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        self._send_json(
            {
                "ok": True,
                "recognized": result.recognized,
                "faces": result.faces,
                "text": result.message,
            }
        )

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        return json.loads(raw_body.decode("utf-8"))

    def _send_empty(self, status: int) -> None:
        self.send_response(status)
        self._send_cors_headers()
        self.end_headers()

    def _send_json(self, body: dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(body).encode("utf-8")

        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:5173")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), IRARequestHandler)
    print(f"IRA backend server listening on http://{HOST}:{PORT}")
    print("Frontend can now send commands to /command.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nIRA backend server stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
