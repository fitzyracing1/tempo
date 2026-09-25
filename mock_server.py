#!/usr/bin/env python3
"""Offline TEMPO sandbox HTTP desk. Stdlib only. Default port 3000."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import json
import sys
from pathlib import Path

from desk import answer, fresh_state
from tempo import decide

STATE = fresh_state()
HERE = Path(__file__).resolve().parent
INDEX = HERE / "static" / "index.html"


def dumps(obj):
    return json.dumps(obj, indent=2).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _cors(self, code=200, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")

    def do_OPTIONS(self):
        self._cors()
        self.end_headers()

    def _read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        raw = self.rfile.read(n).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"_raw": raw}

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            html = INDEX.read_text(encoding="utf-8") if INDEX.exists() else FALLBACK_HTML
            body = html.encode("utf-8")
            self._cors(200, "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/health":
            body = dumps({"ok": True, "service": "tempo-sandbox"})
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/state":
            snap = {k: v for k, v in STATE.items() if k != "log"}
            snap["log_len"] = len(STATE.get("log") or [])
            body = dumps(snap)
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/help":
            body = dumps({
                "endpoints": {
                    "GET /": "chat UI",
                    "GET /state": "current temps, spec, brief",
                    "POST /ask": '{"question": "..."}',
                    "POST /decide": '{"brain":"grok"|"rule"} optional prev/cur/brief',
                    "POST /spec": '{"cur":"..."}',
                    "POST /reset": "{}",
                }
            })
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        body = dumps({"error": "not found", "see": "/help"})
        self._cors(404)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = urlparse(self.path).path
        data = self._read_json()

        if path == "/reset":
            STATE.clear()
            STATE.update(fresh_state())
            body = dumps({"ok": True, "temps": STATE["temps"]})
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/spec":
            cur = data.get("cur") or data.get("spec")
            if not cur:
                body = dumps({"error": "need cur"})
                self._cors(400)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            STATE["prev"] = STATE["cur"]
            STATE["cur"] = str(cur)
            if data.get("brief"):
                STATE["brief"] = str(data["brief"])
            body = dumps({"ok": True, "len": len(STATE["cur"])})
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/decide":
            if data.get("brief"):
                STATE["brief"] = str(data["brief"])
            if data.get("cur"):
                STATE["prev"] = STATE["cur"]
                STATE["cur"] = str(data["cur"])
            brain = data.get("brain") or "grok"
            out = decide(
                brief=STATE["brief"], temps=STATE["temps"],
                prev=STATE["prev"], cur=STATE["cur"], brain=brain,
            )
            STATE["last"] = out
            body = dumps(out)
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/ask":
            q = data.get("question") or data.get("q") or data.get("_raw") or ""
            msg = answer(str(q), STATE)
            rec = {"q": q, "a": msg}
            STATE.setdefault("log", []).append(rec)
            body = dumps({"answer": msg, "question": q})
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/commit":
            out = STATE.get("last") or decide(
                brief=STATE["brief"], temps=STATE["temps"],
                prev=STATE["prev"], cur=STATE["cur"], brain="grok",
            )
            if out["next"] != "FINISH":
                STATE["temps"].append(float(out["t"]))
            body = dumps({"temps": STATE["temps"], "next": out["next"], "t": out["t"]})
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        body = dumps({"error": "not found"})
        self._cors(404)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


FALLBACK_HTML = "<html><body><p>TEMPO desk. POST /ask</p></body></html>"


def main():
    port = 3000
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"TEMPO sandbox http://127.0.0.1:{port}")
    print("GET /  chat   POST /ask  {\"question\":\"what is the next t?\"}")
    server.serve_forever()


if __name__ == "__main__":
    main()
