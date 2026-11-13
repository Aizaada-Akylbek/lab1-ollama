"""Lab 1 chat page server.
Serves index.html on port 8000 and passes questions to Ollama (localhost:11434).
Uses only the Python standard library - nothing to install.
Run:  python3 server.py
"""
import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = os.environ.get("MODEL", "llama3.2:1b")
PORT = 8000
HERE = os.path.dirname(os.path.abspath(__file__))


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        elif self.path == "/api/models":
            try:
                with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=5) as r:
                    names = [m["name"] for m in json.load(r).get("models", [])]
                self._send(200, json.dumps({"models": names, "default": DEFAULT_MODEL}))
            except Exception as e:
                self._send(502, json.dumps({"error": f"Ollama not reachable: {e}"}))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if self.path != "/api/ask":
            return self._send(404, json.dumps({"error": "not found"}))
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length) or b"{}")
            question = (req.get("question") or "").strip()
            model = req.get("model") or DEFAULT_MODEL
            if not question:
                return self._send(400, json.dumps({"error": "Type a question first."}))
            payload = json.dumps({"model": model, "prompt": question, "stream": False}).encode()
            ollama_req = urllib.request.Request(
                OLLAMA_URL + "/api/generate", data=payload,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(ollama_req, timeout=300) as r:
                answer = json.load(r).get("response", "")
            self._send(200, json.dumps({"answer": answer, "model": model}))
        except urllib.error.HTTPError as e:
            self._send(502, json.dumps({"error": f"Ollama error {e.code}: {e.read().decode()[:300]}"}))
        except Exception as e:
            self._send(502, json.dumps({"error": f"Ollama not reachable: {e}. Is 'ollama serve' running?"}))

    def log_message(self, fmt, *args):
        print("[server]", fmt % args)


if __name__ == "__main__":
    print(f"Chat page running on port {PORT} (model: {DEFAULT_MODEL})")
    print("Open the PORTS tab and click the globe icon next to port 8000.")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
