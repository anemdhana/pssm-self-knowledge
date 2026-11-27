#!/usr/bin/env python3
"""
Local server for PSSM Self Knowledge.

  python serve.py
  start.cmd

UI: http://127.0.0.1:8766/

Page and style edits refresh the open browser. Python edits restart this
process in place, so the start window stays open.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

HOST = "127.0.0.1"
PORT = 8766

LOCK = threading.Lock()
STATE = {
  "mtimes": {},
  "boot": f"{time.time_ns():x}",
}
LIVE_SNIPPET = """<script>
(function(){
  var page = location.pathname;
  var gen = null;
  function tick(){
    fetch("/api/live?page=" + encodeURIComponent(page), {cache:"no-store"})
      .then(function(r){return r.json();})
      .then(function(data){
        if (!data || !data.gen) return;
        if (gen === null) gen = data.gen;
        else if (data.gen !== gen) location.reload();
      })
      .catch(function(){});
  }
  setInterval(tick, 500);
})();
</script>
""".encode("utf-8")


class Server(ThreadingHTTPServer):
  allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
  server_version = "PSSMSelfKnowledge/1.0"

  def log_message(self, fmt: str, *args) -> None:
    if self.path.startswith("/api/live"):
      return
    sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

  def _send_bytes(self, code: int, data: bytes, content_type: str) -> None:
    self.send_response(code)
    self.send_header("Content-Type", content_type)
    self.send_header("Content-Length", str(len(data)))
    self.send_header("Cache-Control", "no-store")
    self.end_headers()
    self.wfile.write(data)

  def _send_json(self, code: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    self._send_bytes(code, body, "application/json; charset=utf-8")

  def do_GET(self) -> None:
    parsed = urllib.parse.urlparse(self.path)
    path = urllib.parse.unquote(parsed.path)

    if path == "/api/health":
      self._send_json(200, {"ok": True})
      return

    if path == "/api/live":
      page = urllib.parse.parse_qs(parsed.query).get("page", ["/"])[0]
      self._send_json(200, {"ok": True, "gen": page_gen(page)})
      return

    if path in ("/", "/index.html"):
      path = "/index.html"
    elif path.endswith("/"):
      path = path + "index.html"

    if path == "/README.md" and (ROOT / "README.md").is_file():
      data = (ROOT / "README.md").read_bytes()
      self._send_bytes(200, data, "text/markdown; charset=utf-8")
      return

    rel = path.lstrip("/")
    if rel.endswith(".html") or rel == "":
      try:
        from pages import render

        html_text = render(rel or "index.html")
      except Exception as exc:
        self._send_bytes(500, str(exc).encode("utf-8"), "text/plain; charset=utf-8")
        return
      if html_text is not None:
        self._send_bytes(200, inject_live(html_text.encode("utf-8")), "text/html; charset=utf-8")
        return

    target = (STATIC / rel).resolve()
    if target.is_dir():
      target = target / "index.html"
    if not str(target).startswith(str(STATIC.resolve())) or not target.is_file():
      self._send_json(404, {"ok": False, "error": "Not found"})
      return
    data = target.read_bytes()
    if target.suffix.lower() == ".css":
      ctype = "text/css; charset=utf-8"
    elif target.suffix.lower() == ".js":
      ctype = "text/javascript; charset=utf-8"
    else:
      ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    self._send_bytes(200, data, ctype)

  def do_POST(self) -> None:
    parsed = urllib.parse.urlparse(self.path)
    if parsed.path == "/api/beautify":
      self._post_beautify(parsed)
      return
    self._send_json(404, {"ok": False, "error": "Not found"})

  def _read_body(self, max_bytes: int = 1_500_000) -> bytes | None:
    length = int(self.headers.get("Content-Length") or "0")
    if length <= 0 or length > max_bytes:
      self._send_json(413, {"ok": False, "error": "The request body is empty or too large."})
      return None
    return self.rfile.read(length)

  def _post_beautify(self, parsed: urllib.parse.ParseResult) -> None:
    raw = self._read_body()
    if raw is None:
      return
    query = urllib.parse.parse_qs(parsed.query)
    name = query.get("name", ["reading.txt"])[0]
    mode = (query.get("mode", ["beautify"])[0] or "beautify").strip().lower()
    if mode not in ("format", "beautify"):
      self._send_json(400, {"ok": False, "error": "Mode must be format or beautify."})
      return
    blurb = query.get("blurb", ["0"])[0].lower() in ("1", "true", "yes", "on")
    if mode == "format":
      blurb = False
    speaker = (query.get("speaker", [""])[0] or "").strip()
    lang_params = query.get("lang") or query.get("langs") or ["original"]
    langs: list[str] = []
    for item in lang_params:
      for part in str(item).replace(";", ",").split(","):
        part = part.strip().lower()
        if part:
          langs.append(part)
    words_raw = (query.get("words", [""])[0] or "").strip()
    word_limit = None
    if mode == "beautify" and words_raw:
      try:
        word_limit = int(words_raw)
      except ValueError:
        self._send_json(400, {"ok": False, "error": "Word limit must be a whole number."})
        return
    try:
      text = raw.decode("utf-8")
    except UnicodeDecodeError:
      self._send_json(400, {"ok": False, "error": "The file must be UTF-8 text."})
      return
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
      sys.path.insert(0, scripts)
    from beautify_reading import BeautifyError, beautify_downloads

    try:
      files = beautify_downloads(
        text,
        source_name=name or "reading.txt",
        mode=mode,
        blurb=blurb,
        word_limit=word_limit,
        speaker=speaker or None,
        langs=langs,
      )
    except BeautifyError as exc:
      self._send_json(400, {"ok": False, "error": str(exc)})
      return
    first = files[0]
    self._send_json(
      200,
      {
        "ok": True,
        "html": first["html"],
        "filename": first["filename"],
        "files": files,
        "mode": mode,
        "blurb": blurb,
        "langs": [item["lang"] for item in files],
      },
    )


def normalize_page(page: str) -> str:
  page = urllib.parse.unquote(page.split("?", 1)[0].split("#", 1)[0])
  if page in ("", "/"):
    return "index.html"
  page = page.lstrip("/")
  if page.endswith("/"):
    page += "index.html"
  return page


def page_gen(page: str) -> str:
  rel = normalize_page(page)
  with LOCK:
    mtimes = dict(STATE["mtimes"])
    boot = STATE["boot"]
  keys = ["site.json", "content/" + rel]
  keys.extend(
    key for key in mtimes
    if key.startswith("static/css/") or key.startswith("static/assets/")
  )
  folder = str(Path(rel).parent.as_posix())
  if rel.endswith("index.html"):
    keys.extend(key for key in mtimes if key.startswith("content/" + folder + "/"))
  if rel == "index.html":
    keys.append("static/shell.js")
  parts = [str(boot)]
  for key in sorted(set(keys)):
    parts.append(f"{key}:{mtimes.get(key, 0)}")
  return hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()[:12]


def inject_live(data: bytes) -> bytes:
  if b"/api/live?page=" in data:
    return data
  lower = data.lower()
  at = lower.rfind(b"</body>")
  if at == -1:
    return data + LIVE_SNIPPET
  return data[:at] + LIVE_SNIPPET + data[at:]


def scan_docs() -> dict[str, int]:
  found = {}

  def add_tree(root: Path, prefix: str) -> None:
    if not root.exists():
      return
    if root.is_file():
      found[prefix] = root.stat().st_mtime_ns
      return
    for path in root.rglob("*"):
      if not path.is_file():
        continue
      try:
        found[prefix + path.relative_to(root).as_posix()] = path.stat().st_mtime_ns
      except OSError:
        continue

  add_tree(ROOT / "content", "content/")
  add_tree(STATIC, "static/")
  add_tree(ROOT / "site.json", "site.json")
  return found


def python_stamp() -> tuple[tuple[str, int], ...]:
  paths = [ROOT / "serve.py", ROOT / "pages.py"]
  scripts = ROOT / "scripts"
  if scripts.is_dir():
    paths.extend(scripts.rglob("*.py"))
  stamps = []
  for path in paths:
    try:
      stamps.append((str(path.resolve()), path.stat().st_mtime_ns))
    except OSError:
      continue
  return tuple(sorted(stamps))


def watch(server: Server, reload_flag: list[bool]) -> None:
  seen = python_stamp()
  while True:
    time.sleep(0.4)
    try:
      found = scan_docs()
    except OSError:
      continue
    with LOCK:
      STATE["mtimes"] = found
    current = python_stamp()
    if current == seen:
      continue
    time.sleep(0.3)
    if python_stamp() == seen:
      continue
    print("Python changed. Restarting server…", flush=True)
    reload_flag[0] = True
    server.shutdown()
    return


def serve(args) -> None:
  if not (ROOT / "site.json").is_file():
    raise SystemExit(f"Missing catalog: {ROOT / 'site.json'}")

  with LOCK:
    STATE["mtimes"] = scan_docs()

  server = Server((args.host, args.port), Handler)
  reload_flag = [False]
  threading.Thread(target=watch, args=(server, reload_flag), daemon=True).start()

  url = f"http://{args.host}:{args.port}/"
  print(f"PSSM Self Knowledge → {url}", flush=True)
  print("Page edits reload the browser. Python edits restart this server.", flush=True)
  print("Press Ctrl+C to stop.", flush=True)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    print("\nStopped.", flush=True)
    server.server_close()
    raise SystemExit(0)
  server.server_close()
  if reload_flag[0]:
    time.sleep(0.2)
    raise SystemExit(75)


RELOAD_EXIT = 75


def main(argv: list[str] | None = None) -> None:
  import argparse

  parser = argparse.ArgumentParser(description="PSSM Self Knowledge local server")
  parser.add_argument("--host", default=HOST)
  parser.add_argument("--port", type=int, default=PORT)
  parser.add_argument("--no-browser", action="store_true", help="Do not open a browser tab")
  args = parser.parse_args(argv)

  if os.environ.get("PSSM_SERVER_CHILD") == "1":
    serve(args)
    return

  if not (ROOT / "site.json").is_file():
    raise SystemExit(f"Missing catalog: {ROOT / 'site.json'}")

  url = f"http://{args.host}:{args.port}/"
  if not args.no_browser:
    try:
      webbrowser.open(url)
    except Exception:
      pass

  env = os.environ.copy()
  env["PSSM_SERVER_CHILD"] = "1"
  command = [sys.executable, *sys.argv]
  while True:
    try:
      code = subprocess.call(command, env=env)
    except KeyboardInterrupt:
      print("\nStopped.", flush=True)
      return
    if code != RELOAD_EXIT:
      raise SystemExit(code)
    print("Restarted.", flush=True)


if __name__ == "__main__":
  main()
