import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from logic import build_assistant_response

BASE_DIR = Path(__file__).parent


class AssistantHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str = "text/html"):
        if not path.exists() or not path.is_file():
            self.send_error(404, "Not Found")
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ["/", "/assistant"]:
            return self._send_file(BASE_DIR / "templates" / "assistant.html")

        if self.path == "/static/app.js":
            return self._send_file(BASE_DIR / "static" / "app.js", "text/javascript")

        if self.path == "/static/style.css":
            return self._send_file(BASE_DIR / "static" / "style.css", "text/css")

        self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path != "/api/assistant":
            self.send_error(404, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length else b"{}"

        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return self._send_json({"error": "Invalid JSON payload"}, status=400)

        user_query = payload.get("query", "")
        response = build_assistant_response(user_query)
        return self._send_json(response)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8000), AssistantHandler)
    print("Serving on http://0.0.0.0:8000")
    server.serve_forever()
