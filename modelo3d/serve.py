"""Servidor local del visor 3D. Sirve esta carpeta y guarda renders (POST /save?name=xxx) en ./renders"""
import base64, os, re, sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.abspath(__file__))
RENDERS = os.path.join(ROOT, "renders")
os.makedirs(RENDERS, exist_ok=True)

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/save":
            self.send_error(404); return
        name = re.sub(r"[^a-zA-Z0-9_-]", "", parse_qs(u.query).get("name", ["render"])[0]) or "render"
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        data = base64.b64decode(body.split(",", 1)[1])
        with open(os.path.join(RENDERS, name + ".png"), "wb") as f:
            f.write(data)
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5198
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
