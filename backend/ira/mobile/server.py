import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import time

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    pass

class MobileHandler(BaseHTTPRequestHandler):
    # Assistant instance injected during server creation
    assistant = None

    def _send_json(self, status_code: int, payload: dict):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

    def do_GET(self):
        if self.path == '/api/v1/health':
            self._send_json(200, {"ok": True})
        elif self.path == '/api/v1/ping':
            self._send_json(200, {"alive": True})
        elif self.path == '/api/v1/status':
            # Richer metadata per Change 4
            
            # Count goals if the assistant supports it safely
            goals_count = 0
            if hasattr(self.assistant, '_goal_manager') or hasattr(MobileHandler.assistant, '_goal_manager'):
                try:
                    from ira.assistant import get_all_goals
                    goals_count = len(get_all_goals())
                except ImportError:
                    pass
                    
            self._send_json(200, {
                "running": True,
                "assistant": "IRA",
                "version": "0.1",
                "device": "Windows",
                "goals": goals_count,
                "memory": True
            })
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/v1/command':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_json(400, {"error": "Missing payload"})
                return
                
            try:
                body = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(body)
                command = data.get("command", "")
            except Exception as e:
                self._send_json(400, {"error": f"Invalid JSON: {str(e)}"})
                return

            if not command:
                self._send_json(400, {"error": "Missing 'command'"})
                return

            t_start = time.perf_counter()
            try:
                response = self.assistant.handle(command)
                handled = getattr(response, 'handled', True)
                text = getattr(response, 'text', str(response))
            except Exception as e:
                handled = False
                text = f"Server Error: {str(e)}"
                
            t_end = time.perf_counter()
            exec_ms = int((t_end - t_start) * 1000)

            self._send_json(200, {
                "handled": handled,
                "response": text,
                "execution_ms": exec_ms
            })
        else:
            self.send_response(404)
            self.end_headers()


class MobileServer:
    def __init__(self, assistant, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.assistant = assistant
        self.server = None
        self._thread = None

    def start(self):
        if self.server:
            return
            
        MobileHandler.assistant = self.assistant
        
        # Avoid "Address already in use" errors during dev restarts
        ThreadedHTTPServer.allow_reuse_address = True
        self.server = ThreadedHTTPServer((self.host, self.port), MobileHandler)
        
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None
            
    def is_running(self):
        return self.server is not None and self._thread is not None and self._thread.is_alive()
