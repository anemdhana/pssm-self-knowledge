#!/usr/bin/env python3
"""Turn an HTML file into an article reading.

The title is the page heading. The date is taken from the HTML when one is
present. When the HTML has no date, the date is today. A leading
"Newsletter blurb:" label is left off the title.

  python scripts/article_reading.py talk.html
  python scripts/article_reading.py talk.html -o talk-reading.html
  python scripts/article_reading.py talk.html --date 2026-11-24 --author "Dr. Lakshmi Newton"
  python scripts/article_reading.py talk.html --fragment --chrome lakshmi -o content/readings/talk.html
"""

from __future__ import annotations

import argparse
import calendar
import html
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from beautify_reading import BeautifyError, clean_fragment, language_of  # noqa: E402

ARTICLE_CSS = """
body {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  color: #2a241f;
  background: #f6efe6;
  line-height: 1.75;
}
article {
  box-sizing: border-box;
  max-width: 40em;
  margin: 0 auto;
  padding: 1.4em 1.15em 2.6em;
}
.reading-author {
  margin: 0;
  font-size: 1.02em;
  font-style: normal;
  color: #2a241f;
}
.reading-date {
  margin: 0.15em 0 1.15em;
  font-size: 0.95em;
  font-style: italic;
  color: #7a6a5a;
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

TITLE_PREFIX = re.compile(
    r"^\s*(?:newsletter\s+blurb|న్యూస్\u200c?లెటర్\s+బ్లర్బ్)\s*:\s*",
    re.IGNORECASE,
)
WORD_COUNT = re.compile(r"పదాల\s*సంఖ్య|word\s*count|ಪದಗಳ\s*ಸಂಖ್ಯೆ", re.IGNORECASE)
MONTHS = {}
for number, name in enumerate(calendar.month_name):
    if name:
        MONTHS[name.lower()] = number
for number, name in enumerate(calendar.month_abbr):
    if name:
        MONTHS[name.lower()] = number
MONTH_PATTERN = "|".join(sorted((re.escape(name) for name in MONTHS), key=len, reverse=True))


class ArticleError(Exception):
    pass


def format_date(value: date) -> str:
    return f"{value.day} {calendar.month_name[value.month]} {value.year}"


def date_line(value: date, note: str = "") -> str:
    label = format_date(value)
    note = note.strip(" ·-")
    if note:
        return f"{label} · {note}"
    return label


def split_date_arg(text: str) -> tuple[date, str]:
    parsed = parse_date(text)
    if parsed is None:
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d").date()
        except ValueError:
            parsed = None
    if parsed is None:
        raise ArticleError(f"Could not read this date: {text}")
    note = text
    for pattern in (
        r"\b\d{4}-\d{2}-\d{2}\b",
        rf"\b\d{{1,2}}\s+(?:{MONTH_PATTERN})\.?\s+\d{{4}}\b",
        rf"\b(?:{MONTH_PATTERN})\.?\s+\d{{1,2}},?\s+\d{{4}}\b",
        r"\b\d{1,2}[./-]\d{1,2}[./-]\d{4}\b",
    ):
        note, count = re.subn(pattern, " ", note, count=1, flags=re.I)
        if count:
            break
    return parsed, note.strip(" ·-")


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_date(text: str) -> date | None:
    """Read the first calendar date in a string."""
    found = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if found:
        parsed = _safe_date(int(found.group(1)), int(found.group(2)), int(found.group(3)))
        if parsed:
            return parsed
    found = re.search(rf"\b(\d{{1,2}})\s+({MONTH_PATTERN})\.?\s+(\d{{4}})\b", text, re.I)
    if found:
        parsed = _safe_date(int(found.group(3)), MONTHS[found.group(2).lower()], int(found.group(1)))
        if parsed:
            return parsed
    found = re.search(rf"\b({MONTH_PATTERN})\.?\s+(\d{{1,2}}),?\s+(\d{{4}})\b", text, re.I)
    if found:
        parsed = _safe_date(int(found.group(3)), MONTHS[found.group(1).lower()], int(found.group(2)))
        if parsed:
            return parsed
    found = re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b", text)
    if found:
        return _safe_date(int(found.group(3)), int(found.group(2)), int(found.group(1)))
    return None


def _meta_content(raw: str, name: str) -> str:
    pattern = (
        rf'<meta\b[^>]*?(?:name|property|itemprop)\s*=\s*["\']{re.escape(name)}["\'][^>]*?'
        rf'content\s*=\s*["\'](.*?)["\']'
        rf'|<meta\b[^>]*?content\s*=\s*["\'](.*?)["\'][^>]*?'
        rf'(?:name|property|itemprop)\s*=\s*["\']{re.escape(name)}["\']'
    )
    found = re.search(pattern, raw, re.I | re.S)
    if not found:
        return ""
    return html.unescape(found.group(1) or found.group(2) or "").strip()


def _plain(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    return TITLE_PREFIX.sub("", title).strip()


def _site_fragment(raw: str) -> tuple[dict, str] | None:
    text = raw.lstrip("\ufeff")
    if not text.startswith("<!--site"):
        return None
    end = text.find("-->")
    if end < 0:
        return None
    try:
        meta = json.loads(text[len("<!--site"):end])
    except json.JSONDecodeError:
        return None
    return meta, text[end + 3:].strip()


def _source_date(raw: str) -> date | None:
    for name in ("article:published_time", "datePublished", "date", "pubdate"):
        content = _meta_content(raw, name)
        if content:
            parsed = parse_date(content[:40])
            if parsed:
                return parsed
    found = re.search(r'<time\b[^>]*\bdatetime\s*=\s*["\']([^"\']+)["\']', raw, re.I)
    if found:
        parsed = parse_date(found.group(1)[:40])
        if parsed:
            return parsed
    return None


def _source_author(raw: str) -> str:
    return _meta_content(raw, "author")


def _source_title(raw: str) -> str:
    found = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
    if not found:
        return ""
    return clean_title(re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", found.group(1)))))


def _take_h1(fragment: str) -> tuple[str, str]:
    found = re.search(r"<h1\b[^>]*>(.*?)</h1>", fragment, re.I | re.S)
    if not found:
        return "", fragment.strip()
    title = clean_title(_plain(found.group(1)))
    body = (fragment[:found.start()] + fragment[found.end():]).strip()
    body = re.sub(r"^</h1>\s*", "", body)
    return title, body


def _drop_word_counts(fragment: str) -> str:
    def keep(match: re.Match[str]) -> str:
        if WORD_COUNT.search(_plain(match.group(0))):
            return ""
        return match.group(0)

    return re.sub(r"<p\b[^>]*>.*?</p>", keep, fragment, flags=re.I | re.S).strip()


def _only_date(text: str) -> date | None:
    parsed = parse_date(text)
    if not parsed:
        return None
    patterns = (
        r"\b\d{4}-\d{2}-\d{2}\b",
        rf"\b\d{{1,2}}\s+(?:{MONTH_PATTERN})\.?\s+\d{{4}}\b",
        rf"\b(?:{MONTH_PATTERN})\.?\s+\d{{1,2}},?\s+\d{{4}}\b",
        r"\b\d{1,2}[./-]\d{1,2}[./-]\d{4}\b",
    )
    leftover = text
    for pattern in patterns:
        leftover, count = re.subn(pattern, " ", leftover, count=1, flags=re.I)
        if count:
            break
    if leftover.strip(" ,.-·"):
        return None
    return parsed


def _lift_date_paragraph(fragment: str) -> tuple[date | None, str]:
    """Use a paragraph that is only a date, and do not repeat it in the body."""
    found_date: date | None = None

    def keep(match: re.Match[str]) -> str:
        nonlocal found_date
        if found_date is not None:
            return match.group(0)
        parsed = _only_date(_plain(match.group(0)))
        if parsed is None:
            return match.group(0)
        found_date = parsed
        return ""

    body = re.sub(r"<p\b[^>]*>.*?</p>", keep, fragment, flags=re.I | re.S).strip()
    return found_date, body


def article_from_html(
    raw: str,
    source_name: str = "reading.html",
    today: date | None = None,
    author: str | None = None,
    on_date: date | None = None,
    date_note: str = "",
    chrome: str | None = None,
    title: str | None = None,
) -> dict:
    text = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise ArticleError("The HTML file is empty.")
    site = _site_fragment(text)
    if site:
        meta, body_html = site
        text = body_html or text
    else:
        meta = {}
    try:
        fragment = clean_fragment(text)
    except BeautifyError as exc:
        raise ArticleError(str(exc)) from exc
    fragment = _drop_word_counts(fragment)
    heading, body = _take_h1(fragment)
    chosen_title = clean_title(title or "") if title else ""
    if not chosen_title:
        chosen_title = clean_title(str(meta.get("h1") or heading or _source_title(raw)))
    if not chosen_title:
        chosen_title = clean_title(Path(source_name).stem.replace("-", " ").replace("_", " "))
    if not chosen_title:
        raise ArticleError("This HTML has no title.")
    lifted, body = _lift_date_paragraph(body)
    chosen = on_date or _source_date(raw) or parse_date(str(meta.get("date") or "")) or lifted or parse_date(chosen_title)
    if chosen is None:
        chosen = today or date.today()
    spoken_by = (author or _source_author(raw) or str(meta.get("author") or "")).strip()
    lang = str(meta.get("lang") or language_of(chosen_title + "\n" + body))
    return {
        "title": chosen_title,
        "date": date_line(chosen, date_note if on_date else ""),
        "author": spoken_by,
        "lang": lang,
        "chrome": (chrome or str(meta.get("chrome") or "")).strip(),
        "body": body.strip(),
    }


def article_document(article: dict) -> str:
    author = f'\n    <p class="reading-author">{html.escape(article["author"])}</p>' if article.get("author") else ""
    body = article["body"]
    reading = f"\n{body}\n" if body else "\n"
    return f"""<!DOCTYPE html>
<html lang="{html.escape(article["lang"])}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(article["title"])}</title>
  <style>{ARTICLE_CSS}</style>
</head>
<body>
  <article class="post-card">{author}
    <p class="reading-date">{html.escape(article["date"])}</p>
    <h1>{html.escape(article["title"])}</h1>{reading}  </article>
</body>
</html>
"""


def article_fragment(article: dict) -> str:
    meta = {
        "layout": "reading",
        "lang": article["lang"],
        "title": article["title"],
        "h1": article["title"],
        "date": article["date"],
    }
    if article.get("chrome"):
        meta["chrome"] = article["chrome"]
    header = json.dumps(meta, ensure_ascii=False, indent=2)
    body = article["body"].strip()
    return f"<!--site\n{header}\n-->\n{body}\n" if body else f"<!--site\n{header}\n-->\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Turn HTML into an article reading")
    parser.add_argument("html", type=Path, help="Source HTML file")
    parser.add_argument("-o", "--output", type=Path, help="File to write (default: beside the HTML)")
    parser.add_argument(
        "--date",
        help="Date to use, such as 2026-11-24 or 2026-11-24 · Kartika Purnima. Otherwise the HTML date, or today.",
    )
    parser.add_argument("--author", help="Speaker name to show above the date")
    parser.add_argument("--title", help="Reading title (otherwise taken from the HTML)")
    parser.add_argument("--fragment", action="store_true", help="Write a content fragment for this site")
    parser.add_argument("--chrome", help="Author chrome for a fragment, such as lakshmi or patriji")
    args = parser.parse_args(argv)
    source = args.html
    if not source.is_file():
        print(f"No such file: {source}", file=sys.stderr)
        return 1
    chosen: date | None = None
    note = ""
    if args.date:
        try:
            chosen, note = split_date_arg(args.date)
        except ArticleError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    try:
        article = article_from_html(
            source.read_text(encoding="utf-8"),
            source.name,
            author=args.author,
            on_date=chosen,
            date_note=note,
            chrome=args.chrome,
            title=args.title,
        )
    except ArticleError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.fragment and not article.get("chrome"):
        print("A site fragment needs --chrome, for example lakshmi or patriji.", file=sys.stderr)
        return 1
    page = article_fragment(article) if args.fragment else article_document(article)
    output = args.output
    if output is None:
        output = source.with_name(f"{source.stem}-reading.html")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8", newline="\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
