#!/usr/bin/env python3
"""Turn a rough Markdown reading into a Kindle HTML page.

Uses the free Gemini API. The model may add punctuation, quotation marks,
and paragraph breaks. It must not add ideas.

  python scripts/beautify_reading.py reading.md
  python scripts/beautify_reading.py reading.md -o reading.html

Set GEMINI_API_KEY in a .env file next to this repository.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = "gemini-3.5-flash-lite"
FREE_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
)
MAX_CHARS = 400_000

SYSTEM = """You only punctuate a reading. The source may be English, Telugu, or Kannada.

Repeat the speaker's words in the same order. Do not rewrite, translate, summarise, or add a title.

You may insert commas, full stops, question marks, and quotation marks. Put each paragraph in <p>. Put a spoken quotation in <blockquote>. If the source already has a heading, use <h1> or <h2>. If it is questions and answers, add class="question" or class="answer".

Return only those HTML tags. No markdown and no commentary.

Example
Source: the breath is prana
Output: <p>The breath is prana.</p>"""

READING_CSS = """
body {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  color: #2a241f;
  background: #f6efe6;
  line-height: 1.75;
}
.reading {
  box-sizing: border-box;
  max-width: 40em;
  margin: 0 auto;
  padding: 1.4em 1.15em 2.6em;
}
h1 {
  margin: 0 0 0.8em;
  font-size: 1.45em;
  font-weight: normal;
  line-height: 1.35;
  color: #3d2a18;
}
h2, h3 {
  margin: 1.5em 0 0.45em;
  font-size: 1.12em;
  font-weight: normal;
  line-height: 1.35;
  color: #6e4a25;
  border-bottom: 1px solid rgba(186, 122, 58, 0.35);
  padding-bottom: 0.15em;
}
p {
  margin: 0 0 0.95em;
  font-size: 1.05em;
  orphans: 2;
  widows: 2;
}
blockquote {
  margin: 1em 0 1.1em;
  padding: 0.55em 0.9em;
  background: #fff8eb;
  border-left: 4px solid #ba7a3a;
}
blockquote p:last-child { margin-bottom: 0; }
.question { font-weight: bold; color: #3d2f22; }
ul, ol { margin: 0 0 1em; padding-left: 1.3em; }
li { margin: 0 0 0.4em; }
"""

ALLOWED = {"h1", "h2", "h3", "p", "blockquote", "em", "strong", "br", "ul", "ol", "li"}
CLASSES = {"question", "answer", "note", "closing", "intro"}


class BeautifyError(Exception):
    pass


class _Clean(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            self.skip += 1
            return
        if self.skip or tag not in ALLOWED:
            return
        if tag == "br":
            self.parts.append("<br>")
            return
        kept = []
        for key, value in attrs:
            if key == "class" and value:
                kept.extend(part for part in value.split() if part in CLASSES)
        if kept:
            self.parts.append(f'<{tag} class="{" ".join(kept)}">')
        else:
            self.parts.append(f"<{tag}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1
            return
        if self.skip or tag not in ALLOWED or tag == "br":
            return
        self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self.skip or not data:
            return
        self.parts.append(html.escape(data))


def _env_file() -> dict[str, str]:
    path = ROOT / ".env"
    found: dict[str, str] = {}
    if not path.is_file():
        return found
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        found[key.strip()] = value.strip().strip('"').strip("'")
    return found


def api_key_from_env() -> str:
    file_values = _env_file()
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "PSSM_LLM_KEY"):
        value = file_values.get(name, "").strip() or os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def language_of(text: str) -> str:
    telugu = sum(1 for char in text if "\u0c00" <= char <= "\u0c7f")
    kannada = sum(1 for char in text if "\u0c80" <= char <= "\u0cff")
    if telugu or kannada:
        return "te" if telugu >= kannada else "kn"
    return "en"


def clean_fragment(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^```(?:html)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    body = re.search(r"<body[^>]*>(.*)</body>", text, flags=re.I | re.S)
    if body:
        text = body.group(1)
    parser = _Clean()
    parser.feed(text)
    fragment = "".join(parser.parts).strip()
    if fragment and not re.search(r"<(?:p|h1|h2|h3|blockquote|ul|ol|li)\b", fragment, re.I):
        parts = [part.strip() for part in re.split(r"\n\s*\n|\n", fragment) if part.strip()]
        fragment = "\n".join(f"<p>{part}</p>" for part in parts)
    if fragment:
        return fragment
    paragraphs = [html.escape(part.strip()) for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        raise BeautifyError("The reading came back empty.")
    return "\n".join(f"<p>{part}</p>" for part in paragraphs)


def document_title(fragment: str, source_name: str) -> str:
    match = re.search(r"<h1[^>]*>(.*?)</h1>", fragment, flags=re.S)
    if match:
        title = re.sub(r"<[^>]+>", "", match.group(1))
        title = html.unescape(title).strip()
        if title:
            return title
    stem = Path(source_name).stem.replace("-", " ").replace("_", " ").strip()
    return stem or "Reading"


def reading_document(fragment: str, source_name: str) -> str:
    title = document_title(fragment, source_name)
    lang = language_of(fragment)
    return f"""<!DOCTYPE html>
<html lang="{html.escape(lang)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{READING_CSS}</style>
</head>
<body>
  <main class="reading">
{fragment}
  </main>
</body>
</html>
"""


def _model_order() -> list[str]:
    chosen = os.environ.get("PSSM_LLM_MODEL", MODEL).strip() or MODEL
    models = [chosen]
    for name in FREE_MODELS:
        if name not in models:
            models.append(name)
    return models


def _is_busy(status: int, message: str) -> bool:
    if status in (429, 500, 503):
        return True
    lowered = message.lower()
    return any(
        phrase in lowered
        for phrase in ("high demand", "overloaded", "unavailable", "resource exhausted", "try again later")
    )


def _gemini_once(markdown: str, key: str, model: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": markdown}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 16384},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        message = detail
        try:
            message = json.loads(detail)["error"]["message"]
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        lowered = message.lower()
        if exc.code in (401, 403) or "api key" in lowered:
            raise BeautifyError(f"Gemini could not prepare this reading. {message}") from exc
        if exc.code == 404 or "not found" in lowered or "not supported" in lowered:
            raise BeautifyError(f"skip:{model}: {message}") from exc
        if _is_busy(exc.code, message):
            raise BeautifyError(f"busy:{model}: {message}") from exc
        raise BeautifyError(f"Gemini could not prepare this reading. {message}") from exc
    except urllib.error.URLError as exc:
        raise BeautifyError(f"Could not reach Gemini. {exc.reason}") from exc

    candidates = data.get("candidates") or []
    if not candidates:
        raise BeautifyError(f"busy:{model}: empty response")
    candidate = candidates[0]
    if candidate.get("finishReason") == "MAX_TOKENS":
        raise BeautifyError("This reading is too long for one pass. Split the Markdown and try again.")
    parts = ((candidate.get("content") or {}).get("parts") or [])
    texts = [part.get("text", "") for part in parts if part.get("text") and not part.get("thought")]
    if not texts:
        raise BeautifyError(f"busy:{model}: empty response")
    return "\n".join(texts)


def _gemini(markdown: str, key: str) -> str:
    for model in _model_order():
        for attempt in range(2):
            try:
                return _gemini_once(markdown, key, model)
            except BeautifyError as exc:
                text = str(exc)
                if text.startswith("skip:"):
                    print(f"{model} is not available. Trying another free model…", file=sys.stderr, flush=True)
                    break
                if not text.startswith("busy:"):
                    raise
                print(f"{model} is busy. Trying again…", file=sys.stderr, flush=True)
                time.sleep(2 if attempt == 0 else 4)
    raise BeautifyError("Gemini is busy right now. Wait a minute and prepare the same file again.")


def beautify_markdown(markdown: str, source_name: str = "reading.md", api_key: str | None = None) -> str:
    text = markdown.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise BeautifyError("The Markdown file is empty.")
    if len(text) > MAX_CHARS:
        raise BeautifyError("This Markdown file is too long. Split it and try again.")
    key = (api_key or "").strip() or api_key_from_env()
    if not key:
        raise BeautifyError(
            "Set GEMINI_API_KEY in .env. A free key is at https://aistudio.google.com/apikey"
        )
    fragment = clean_fragment(_gemini(text, key))
    return reading_document(fragment, source_name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Beautify a Markdown reading into Kindle HTML")
    parser.add_argument("markdown", type=Path, help="Source .md file")
    parser.add_argument("-o", "--output", type=Path, help="HTML file to write (default: beside the Markdown)")
    args = parser.parse_args(argv)
    source = args.markdown
    if not source.is_file():
        print(f"No such file: {source}", file=sys.stderr)
        return 1
    output = args.output or source.with_suffix(".html")
    try:
        page = beautify_markdown(source.read_text(encoding="utf-8"), source.name)
    except BeautifyError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    output.write_text(page, encoding="utf-8", newline="\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
