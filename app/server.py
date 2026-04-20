from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from app.config import DEFAULT_TOP_K, PORT, STATIC_DIR
from app.runtime import AssistantRuntime


def json_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, indent=2).encode("utf-8")


class AssistantHandler(BaseHTTPRequestHandler):
    runtime = AssistantRuntime()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self._serve_static("index.html")
            return

        if parsed.path.startswith("/static/"):
            self._serve_static(parsed.path.replace("/static/", "", 1))
            return

        if parsed.path == "/api/health":
            self._send_json(type(self).runtime.health())
            return

        if parsed.path == "/api/documents":
            self._send_json({"documents": type(self).runtime.list_documents()})
            return

        if parsed.path == "/api/search":
            query = parse_qs(parsed.query).get("q", [""])[0]
            top_k = int(parse_qs(parsed.query).get("top_k", [str(DEFAULT_TOP_K)])[0])
            results = type(self).runtime.search(query, top_k=top_k)
            self._send_json({"query": query, "results": [item.to_dict() for item in results]})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Route not found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        payload = self._read_json()

        if parsed.path == "/api/ask":
            question = str(payload.get("question", "")).strip()
            top_k = int(payload.get("top_k", DEFAULT_TOP_K))
            answer = type(self).runtime.ask(question, top_k=top_k)
            self._send_json(answer.to_dict())
            return

        if parsed.path == "/api/index/rebuild":
            stats = type(self).runtime.rebuild()
            self._send_json({"status": "rebuilt", **stats})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Route not found")

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length else b"{}"
        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _send_json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_static(self, relative_path: str) -> None:
        safe_path = Path(relative_path).name
        target = STATIC_DIR / safe_path
        if not target.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Static file not found")
            return

        content = target.read_bytes()
        mime_type, _ = mimetypes.guess_type(str(target))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), AssistantHandler)
    runtime = AssistantHandler.runtime
    print(
        "AI-102 Knowledge Assistant running on "
        f"http://127.0.0.1:{PORT} "
        f"(requested mode: {runtime.requested_mode}, active mode: {runtime.active_mode})"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
