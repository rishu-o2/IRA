from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .assistant import IRAAssistant
from .face import FaceRecognitionError, detect_faces

HOST = "0.0.0.0"
PORT = 8765


import time

class IRARequestHandler(BaseHTTPRequestHandler):
    assistant = IRAAssistant()
    platform_components: dict = {}

    def do_OPTIONS(self) -> None:
        self._send_empty(204)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json({"ok": True, "name": "IRA", "features": ["command", "conversation", "face"]})
            return

        if self.path == "/virtual_world":
            self._send_json({
                "ok": True,
                "virtual_world_state": self.assistant.virtual_world.get_status(),
                "modifications": self.assistant.recent_modifications,
            })
            return

        self._send_json({"ok": False, "error": "Not found"}, status=404)

    def do_POST(self) -> None:
        t_req_start = time.perf_counter()
        print(f"[PERF] Request received: {self.path}")

        if self.path == "/command":
            self._handle_command()
            t_req_end = time.perf_counter()
            print(f"[PERF] Total HTTP request: {(t_req_end - t_req_start) * 1000:.0f} ms")
            return

        if self.path == "/face":
            self._handle_face()
            t_req_end = time.perf_counter()
            print(f"[PERF] Total HTTP request: {(t_req_end - t_req_start) * 1000:.0f} ms")
            return

        if self.path == "/listen":
            self._handle_listen()
            t_req_end = time.perf_counter()
            print(f"[PERF] Total HTTP request: {(t_req_end - t_req_start) * 1000:.0f} ms")
            return

        if self.path == "/api/v1/device/register":
            self._handle_api_device_register()
            t_req_end = time.perf_counter()
            return
            
        if self.path == "/api/v1/device/heartbeat":
            self._handle_api_device_heartbeat()
            t_req_end = time.perf_counter()
            return
            
        if self.path == "/api/v1/session":
            self._handle_api_session()
            t_req_end = time.perf_counter()
            return

        self._send_json({"ok": False, "error": "Not found"}, status=404)
        t_req_end = time.perf_counter()
        print(f"[PERF] Total HTTP request: {(t_req_end - t_req_start) * 1000:.0f} ms")

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
                "virtual_world_state": self.assistant.virtual_world.get_status(),
                "modifications": self.assistant.recent_modifications,
            }
        )

    def _handle_face(self) -> None:
        try:
            payload = self._read_json()
            image = str(payload.get("image") or payload.get("image_base64") or "").strip()
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
                "message": result.message,
            }
        )

    def _handle_listen(self) -> None:
        from .voice import listen_for_command
        try:
            text = listen_for_command()
            self._send_json({"ok": True, "text": text})
        except Exception as e:
            self._send_json({"ok": False, "error": str(e)}, status=500)

    def _handle_api_device_register(self) -> None:
        try:
            payload = self._read_json()
            from .device.models import Device, DeviceType, Capability
            device = Device(
                device_id=payload.get("device_id", ""),
                user_id=payload.get("user_id", "default"),
                device_name=payload.get("device_name", "Unknown"),
                device_type=DeviceType(payload.get("device_type", "UNKNOWN")),
                platform=payload.get("platform", ""),
                os_version=payload.get("os_version", ""),
                app_version=payload.get("app_version", ""),
                capabilities={Capability(c) for c in payload.get("capabilities", [])}
            )
            device_manager = self.platform_components.get("device_manager")
            if device_manager:
                device_manager.register_device(device)
            self._send_json({"success": True, "device_secret": "test_secret"})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, status=400)
            
    def _handle_api_device_heartbeat(self) -> None:
        try:
            payload = self._read_json()
            device_id = payload.get("device_id", "")
            device_manager = self.platform_components.get("device_manager")
            if device_manager:
                device_manager.update_last_seen(device_id)
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, status=400)
            
    def _handle_api_session(self) -> None:
        try:
            payload = self._read_json()
            device_id = payload.get("device_id", "")
            session_manager = self.platform_components.get("session_manager")
            session_id = None
            if session_manager:
                session = session_manager.create(device_id)
                session_id = session.session_id
            self._send_json({"success": True, "session_id": session_id, "status": "ACTIVE"})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, status=400)

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
        origin = self.headers.get("Origin", "*")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Credentials", "true")


def main() -> None:
    from .lifecycle.startup import initialize_platform
    from .lifecycle.shutdown import shutdown_platform
    
    components = initialize_platform()
    IRARequestHandler.platform_components = components
    
    # Inject into brain orchestrator
    if hasattr(IRARequestHandler.assistant, "orchestrator"):
        o = IRARequestHandler.assistant.orchestrator
        o._device_manager = components["device_manager"]
        o._session_manager = components["session_manager"]
        o._event_bus = components["event_bus"]
        o._notification_dispatcher = components["notification_dispatcher"]

    server = ThreadingHTTPServer((HOST, PORT), IRARequestHandler)
    
    # Get local IP for network access
    local_ip = HOST if HOST != "0.0.0.0" else "127.0.0.1"
    try:
        import socket
        # Get the actual local network IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    
    print(f"IRA backend server listening on http://{HOST}:{PORT}")
    print(f"Network accessible at: http://{local_ip}:{PORT}")
    print("Frontend can use the unified backend routes: /health, /command, /face, /api/v1/*.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nIRA backend server stopped.")
    finally:
        server.server_close()
        shutdown_platform(components)


if __name__ == "__main__":
    main()
