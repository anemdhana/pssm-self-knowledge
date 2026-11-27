#!/usr/bin/env python3
"""Turn YouTube captions (.txt) into a Kindle HTML reading.

Uses the free Gemini API. Full reading or newsletter blurb (Tools UI / flags),
matching site pieces such as Dr. Lakshmi Newton’s birthday speech.

  python scripts/beautify_reading.py captions.txt
  python scripts/beautify_reading.py captions.txt --blurb --words 450
  python scripts/beautify_reading.py captions.txt -o reading.html

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
DEFAULT_WORDS_FULL = 2500
DEFAULT_WORDS_BLURB = 450

SYSTEM_FORMAT = """Format YouTube captions into a FULL spoken reading for Kindle.

This is FORMAT, not beautify: keep every original word exactly. Only add punctuation and paragraph breaks.

The source is plain captions text (English, Telugu, or Kannada). Ignore leftover timestamps, [Music], and broken wraps — use only the spoken words, in order, unchanged.
{speaker_rule}
Rules:
- Format the transcript without changing any original text (of the kept speech).
- Only add full stops, commas, quotation marks, and other punctuation so it feels like a person is speaking naturally.
- Follow context, intention, and spiritual wisdom. Never alter the meaning or any words.
- Proper paragraph breaks for a pleasant Kindle reading (often short paragraphs).
- Preserve every original word exactly. Only punctuation and paragraph structure are added.
- You may use <blockquote> for clear spoken turns and sparse <strong>/<em> only where they do not change or drop words.
- No section headings. No <h1>/<h2>/<h3>. No title invention. Do not translate. Do not summarise. Do not shorten.

Return only HTML using <p>, <blockquote>, <em>, <strong>, <br>, <ul>, <ol>, <li>. No markdown, no commentary.

Example
Source: this is my birthday a small child I was born
Output: <p>This is my birthday. A small child I was born.</p>"""

SYSTEM_BEAUTIFY = """Beautify YouTube captions into a FULL spoken reading for Kindle (not Format, not a newsletter blurb).

Beautify works differently from Format: you may lightly shape sentences for pleasant conversation-style Kindle reading (Lakshmi birthday full-reading quality). Keep the speaker’s meaning and order. Do not invent teachings. Do not turn the talk into a blurb.

The source is plain captions text (English, Telugu, or Kannada). Ignore timestamps and [Music]-style tags.
{speaker_rule}
{language_rule}
Flow the whole talk — no section headings, no <h1>/<h2>/<h3>, no topic labels.

{length_rule}

Presentation rules:
- Short breath-like paragraphs; natural punctuation and quotation marks.
- Lightly smooth awkward caption grammar for reading comfort — same ideas, same order.
- Stories as short beats; remembered dialogue in <blockquote> with narrative lead-in and a short connective line when natural (“he said” / “అన్నారు” / equivalent in the output language).
- Sparse <strong> for names/key terms; <em> only for short soft emphasis.
- Speaker’s voice throughout (I / we / direct address).

Return only HTML using <p>, <blockquote>, <em>, <strong>, <br>, <ul>, <ol>, <li>. No headings, no markdown, no commentary.

Example
Source: he came and asked will you come with me leave everything from this moment I will not force you and I said at once let us go
Output: <p>He came and asked:</p>
<blockquote><p>“Will you come with me? Leave everything from this moment. I will not force you.”</p></blockquote>
<p>And I said at once — let us go.</p>"""
SYSTEM_BLURB = """Write a NEWSLETTER BLURB in HTML for Kindle from YouTube captions, matching site blurbs such as Dr. Lakshmi Newton’s birthday newsletter blurb.

This is NOT a full transcript. Third-person summary of the talk: warm, clear, complete as a short piece. Ignore timestamps and [Music]-style tags. Do not invent teachings or events.
{speaker_rule}
{language_rule}
{length_rule}

Structure the arc without section headings:
- Opening: setting, occasion, who spoke, what the moment felt like.
- Middle: main themes and one or two key stories in brief.
- Closing: sankalpa or call, then a quiet return.

Use continuous prose — no <h1>/<h2>/<h3>, no topic labels. Prefer short readable paragraphs.
Use a few <blockquote> lines only where a short spoken line carries the heart of the message (as in the site blurbs). Lead with narrative, then the quote, then continue.
Use <strong> sparingly for names; <em> only for a short soft phrase.

Return only HTML using <p>, <blockquote>, <em>, <strong>, <br>, <ul>, <ol>, <li>. No headings, no markdown, no commentary, no “read more” link.

Example shape
<p>On the sacred day… she rose to speak.</p>
<p>She began with reverence…</p>
<blockquote><p>“Will you come with me?”</p></blockquote>
<p>…</p>
<p>She closed with a clear sankalpa…</p>"""

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

ALLOWED = {"p", "blockquote", "em", "strong", "br", "ul", "ol", "li"}
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


def _length_rule(word_limit: int | None, *, blurb: bool) -> str:
    if word_limit is None:
        if blurb:
            return (
                "Length: keep a short newsletter blurb arc without a hard word cap, "
                "but stay concise (prefer under about 800 words). Do not invent filler."
            )
        return (
            "Length: cover the full source content. Do not shorten for a word budget. "
            "Do not invent filler to make it longer."
        )
    return (
        f"Length: stay near or under {word_limit} words. Finish the current thought cleanly; "
        "do not cut mid-sentence. Do not pad to fill the limit."
    )


def _speaker_rule(speaker: str | None) -> str:
    name = (speaker or "").strip()
    if not name:
        return ""
    return (
        f"\nSpeaker filter: extract ONLY the speech of “{name}” "
        "(match common variants of that name). Drop other speakers, hosts, "
        "announcements, and stage chatter that are clearly not them. "
        "If labels are missing, use context to keep only that person’s continuous talk.\n"
    )


OUTPUT_LANGS = ("original", "en", "hi")


def resolve_output_lang(lang: str | None) -> str:
    chosen = (lang or "original").strip().lower()
    if chosen in ("english", "en-in", "en_us"):
        chosen = "en"
    if chosen in ("hindi", "hin", "hi-in"):
        chosen = "hi"
    if chosen not in OUTPUT_LANGS:
        raise BeautifyError("Output language must be original, en, or hi.")
    return chosen


def _language_rule(lang: str) -> str:
    if lang == "en":
        return (
            "\nLanguage: write the entire reading in clear English. "
            "Faithfully convey the speaker’s meaning from the captions. "
            "If the source is Telugu, Kannada, or Hindi, translate into natural English "
            "(keep proper names as spoken). If the source is already English, keep English. "
            "Do not leave body paragraphs in another language.\n"
        )
    if lang == "hi":
        return (
            "\nLanguage: write the entire reading in clear Hindi (Devanagari). "
            "Faithfully convey the speaker’s meaning from the captions. "
            "If the source is Telugu, Kannada, or English, translate into natural Hindi "
            "(keep proper names as spoken). If the source is already Hindi, keep Hindi. "
            "Do not leave body paragraphs in another language.\n"
        )
    return (
        "\nLanguage: write in the same language as the spoken captions "
        "(English, Telugu, Kannada, or Hindi). Do not translate.\n"
    )


def _system_prompt(
    mode: str,
    blurb: bool,
    word_limit: int | None,
    speaker: str | None = None,
    *,
    lang: str = "original",
) -> str:
    speaker_rule = _speaker_rule(speaker)
    if mode == "format":
        return SYSTEM_FORMAT.format(speaker_rule=speaker_rule)
    language_rule = _language_rule(lang)
    if blurb:
        return SYSTEM_BLURB.format(
            speaker_rule=speaker_rule,
            language_rule=language_rule,
            length_rule=_length_rule(word_limit, blurb=True),
        )
    return SYSTEM_BEAUTIFY.format(
        speaker_rule=speaker_rule,
        language_rule=language_rule,
        length_rule=_length_rule(word_limit, blurb=False),
    )


def _gemini_once(markdown: str, key: str, model: str, system: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": markdown}]}],
        "generationConfig": {"temperature": 0.45, "maxOutputTokens": 16384},
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
        raise BeautifyError("This reading is too long for one pass. Split the captions and try again.")
    parts = ((candidate.get("content") or {}).get("parts") or [])
    texts = [part.get("text", "") for part in parts if part.get("text") and not part.get("thought")]
    if not texts:
        raise BeautifyError(f"busy:{model}: empty response")
    return "\n".join(texts)


def _gemini(markdown: str, key: str, system: str) -> str:
    for model in _model_order():
        for attempt in range(2):
            try:
                return _gemini_once(markdown, key, model, system)
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


def normalize_captions(text: str) -> str:
    """Strip common YouTube caption chrome before sending to the model."""
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        if re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?(?:\s*-->\s*\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)?", line):
            continue
        if re.fullmatch(r"\[\s*(?:music|applause|laughter|silence|inaudible)[^\]]*\]", line, flags=re.I):
            continue
        line = re.sub(
            r"^\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?\s+",
            "",
            line,
        )
        line = re.sub(r"\[\s*(?:music|applause|laughter|silence|inaudible)[^\]]*\]", "", line, flags=re.I)
        line = line.strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def resolve_word_limit(word_limit: int | str | None) -> int | None:
    """Return an int limit, or None when empty (full content, no word budget)."""
    if word_limit is None:
        return None
    if isinstance(word_limit, str):
        text = word_limit.strip()
        if not text:
            return None
        try:
            word_limit = int(text)
        except ValueError as exc:
            raise BeautifyError("Word limit must be a whole number, or leave it empty for full content.") from exc
    try:
        value = int(word_limit)
    except (TypeError, ValueError) as exc:
        raise BeautifyError("Word limit must be a whole number, or leave it empty for full content.") from exc
    if value < 50 or value > 20_000:
        raise BeautifyError("Word limit must be between 50 and 20000, or leave it empty for full content.")
    return value


def download_stem(source_name: str, *, mode: str, blurb: bool) -> str:
    stem = Path(source_name or "reading").stem.replace("_", "-").replace(" ", "-") or "reading"
    if blurb:
        return f"{stem}-blurb"
    if mode == "format":
        return f"{stem}-formatted"
    return stem


def download_filename(source_name: str, *, mode: str, blurb: bool, lang: str = "original") -> str:
    stem = download_stem(source_name, mode=mode, blurb=blurb)
    chosen = resolve_output_lang(lang)
    if chosen == "en":
        return f"{stem}-en.html"
    if chosen == "hi":
        return f"{stem}-hi.html"
    return f"{stem}.html"


def beautify_markdown(
    markdown: str,
    source_name: str = "reading.txt",
    api_key: str | None = None,
    *,
    mode: str = "beautify",
    blurb: bool = False,
    word_limit: int | str | None = None,
    speaker: str | None = None,
    lang: str = "original",
) -> str:
    text = normalize_captions(markdown)
    if not text:
        raise BeautifyError("The captions file is empty.")
    if len(text) > MAX_CHARS:
        raise BeautifyError("This captions file is too long. Split it and try again.")
    key = (api_key or "").strip() or api_key_from_env()
    if not key:
        raise BeautifyError(
            "Set GEMINI_API_KEY in .env. A free key is at https://aistudio.google.com/apikey"
        )
    chosen = (mode or "beautify").strip().lower()
    if chosen not in {"format", "beautify"}:
        raise BeautifyError("Mode must be format or beautify.")
    output_lang = "original"
    if chosen == "format":
        blurb = False
        limit = None
    else:
        limit = resolve_word_limit(word_limit)
        output_lang = resolve_output_lang(lang)
    system = _system_prompt(chosen, blurb, limit, speaker=speaker, lang=output_lang)
    fragment = clean_fragment(_gemini(text, key, system))
    return reading_document(fragment, source_name)


def resolve_output_langs(langs: list[str] | str | None) -> list[str]:
    if langs is None:
        return ["original"]
    if isinstance(langs, str):
        parts = [part.strip() for part in langs.replace(";", ",").split(",")]
    else:
        parts = [str(part).strip() for part in langs]
    chosen: list[str] = []
    for part in parts:
        if not part:
            continue
        lang = resolve_output_lang(part)
        if lang not in chosen:
            chosen.append(lang)
    if not chosen:
        raise BeautifyError("Choose at least one output language.")
    return chosen


def beautify_downloads(
    markdown: str,
    source_name: str = "reading.txt",
    api_key: str | None = None,
    *,
    mode: str = "beautify",
    blurb: bool = False,
    word_limit: int | str | None = None,
    speaker: str | None = None,
    langs: list[str] | str | None = None,
) -> list[dict[str, str]]:
    """Return one HTML per selected language (Format always uses original only)."""
    chosen = (mode or "beautify").strip().lower()
    if chosen == "format":
        selected = ["original"]
    else:
        selected = resolve_output_langs(langs)
    pages: list[dict[str, str]] = []
    for lang in selected:
        page = beautify_markdown(
            markdown,
            source_name,
            api_key,
            mode=chosen,
            blurb=blurb,
            word_limit=word_limit,
            speaker=speaker,
            lang=lang,
        )
        pages.append(
            {
                "html": page,
                "filename": download_filename(source_name, mode=chosen, blurb=blurb, lang=lang),
                "lang": lang,
            }
        )
    return pages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Format or beautify YouTube captions (.txt) into Kindle HTML")
    parser.add_argument("captions", type=Path, help="Source captions .txt file")
    parser.add_argument("-o", "--output", type=Path, help="HTML file to write (default: beside the captions)")
    parser.add_argument(
        "--mode",
        choices=("format", "beautify"),
        default="beautify",
        help="format = keep every word (punctuation only); beautify = shaped Kindle reading",
    )
    parser.add_argument("--blurb", action="store_true", help="With beautify: newsletter blurb instead of full reading")
    parser.add_argument("--speaker", help="Optional: keep only this speaker’s speech from multi-speaker captions")
    parser.add_argument(
        "--words",
        type=int,
        default=None,
        help=(
            f"Beautify word limit (UI prefills {DEFAULT_WORDS_FULL} / {DEFAULT_WORDS_BLURB}; "
            "omit for no hard cap; ignored for format)"
        ),
    )
    parser.add_argument(
        "--lang",
        choices=OUTPUT_LANGS,
        default="original",
        help="Beautify output language (default: original transcript language; ignored for format)",
    )
    args = parser.parse_args(argv)
    source = args.captions
    if not source.is_file():
        print(f"No such file: {source}", file=sys.stderr)
        return 1
    try:
        page = beautify_markdown(
            source.read_text(encoding="utf-8"),
            source.name,
            mode=args.mode,
            blurb=args.blurb,
            word_limit=args.words,
            speaker=args.speaker,
            lang=args.lang,
        )
    except BeautifyError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    output = args.output or source.with_name(
        download_filename(source.name, mode=args.mode, blurb=args.blurb, lang=args.lang)
    )
    output.write_text(page, encoding="utf-8", newline="\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
