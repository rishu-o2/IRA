import json
import urllib.request
import urllib.error

class MobileClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.base_url = f"http://{host}:{port}/api/v1"

    def _get(self, endpoint: str) -> dict:
        req = urllib.request.Request(f"{self.base_url}/{endpoint}")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as response:
                body = response.read().decode('utf-8')
                return json.loads(body)
        except urllib.error.URLError as e:
            return {"error": str(e)}

    def _post(self, endpoint: str, payload: dict) -> dict:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"{self.base_url}/{endpoint}",
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as response:
                body = response.read().decode('utf-8')
                return json.loads(body)
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode('utf-8')
                return json.loads(body)
            except Exception:
                return {"error": str(e)}
        except urllib.error.URLError as e:
            return {"error": str(e)}

    def send_command(self, command: str) -> dict:
        return self._post("command", {"command": command})

    def get_status(self) -> dict:
        return self._get("status")

    def health(self) -> dict:
        return self._get("health")
        
    def ping(self) -> dict:
        return self._get("ping")
