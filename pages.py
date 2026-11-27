"""Render one set of readings for the local server and for GitHub Pages."""

from __future__ import annotations

import html
import json
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
CATALOG = ROOT / "site.json"


def load_catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def split_legacy_html(text: str) -> dict:
    """Pull the unique reading out of a full copied page."""

    def grab(pattern: str) -> str:
        import re

        match = re.search(pattern, text, re.S)
        return match.group(1).strip() if match else ""

    lang = grab(r'<html lang="([^"]+)"') or "en"
    return {
        "lang": lang,
        "title": grab(r"<title>(.*?)</title>"),
        "h1": grab(r"<h1>(.*?)</h1>"),
        "eyebrow": grab(r'<p class="eyebrow">(.*?)</p>'),
        "author_detail": grab(r'<div class="author-info">.*?<span>(.*?)</span>'),
        "body": grab(r"</h1>\s*(.*?)\s*</article>"),
    }


def write_fragment(path: Path, meta: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = json.dumps(meta, ensure_ascii=False, indent=2)
    path.write_text(f"<!--site\n{header}\n-->\n{body.strip()}\n", encoding="utf-8", newline="\n")


def _load_fragment(rel: str) -> dict | None:
    path = CONTENT / rel
    if not path.is_file() or path.name.startswith("_"):
        return None
    text = path.read_text(encoding="utf-8")
    if text.startswith("<!--site"):
        end = text.find("-->")
        meta = json.loads(text[len("<!--site"):end])
        body = text[end + 3:].strip()
    else:
        meta, body = {}, text.strip()
    meta["rel"] = rel
    return {"meta": meta, "body": body}


def _pages() -> dict[str, dict]:
    found = {}
    if not CONTENT.is_dir():
        return found
    for path in CONTENT.rglob("*.html"):
        if path.name.startswith("_"):
            continue
        rel = path.relative_to(CONTENT).as_posix()
        page = _load_fragment(rel)
        if page:
            found[rel] = page
    return found


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _prefix(rel: str) -> str:
    depth = rel.count("/")
    return "../" * depth


def _lang_suffix(catalog: dict, lang: str) -> str:
    for item in catalog["languages"]:
        if item["id"] == lang:
            return item["suffix"]
    return ""


def _day_name(day: int, lang: str, catalog: dict) -> str:
    return f"day-{day:02d}{_lang_suffix(catalog, lang)}.html"


def _exists(rel: str) -> bool:
    return (CONTENT / rel).is_file()


def render(rel: str) -> str | None:
    catalog = load_catalog()
    if rel in ("", "index.html"):
        return _shell(catalog)
    series = _series_index(rel, catalog)
    if series:
        return _series(rel, catalog, series)
    page = _load_fragment(rel)
    if page:
        return _reading(page, catalog)
    section = _section_for(rel, catalog)
    if section and section.get("id") == "tools":
        return _tools(rel)
    if section:
        return _hub(rel, catalog, section)
    return None


def build(out: Path) -> int:
    catalog = load_catalog()
    paths = {"index.html"}
    for section in catalog["sections"]:
        start = section["start"]
        if not start.endswith("/"):
            start += "/"
        paths.add(start + "index.html")
        for group in section["groups"]:
            for article in group.get("articles") or []:
                paths.add(article["href"])
    paths.update(_pages())
    if out.exists():
        shutil.rmtree(out)
    count = 0
    for rel in sorted(paths):
        html_text = render(rel)
        if html_text is None:
            continue
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html_text, encoding="utf-8", newline="\n")
        count += 1
    if STATIC.is_dir():
        for path in STATIC.rglob("*"):
            if not path.is_file():
                continue
            dest = out / path.relative_to(STATIC)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return count


def _series_index(rel: str, catalog: dict) -> dict | None:
    for section in catalog["sections"]:
        for group in section["groups"]:
            series = group.get("series")
            if not series:
                continue
            href = series["href"] if series["href"].endswith("/") else series["href"] + "/"
            if rel == href + "index.html":
                return series
    return None


def _section_for(rel: str, catalog: dict) -> dict | None:
    for section in catalog["sections"]:
        start = section["start"] if section["start"].endswith("/") else section["start"] + "/"
        if rel == start + "index.html":
            return section
    return None


def _shell(catalog: dict) -> str:
    starts = {section["id"]: section["start"] for section in catalog["sections"]}
    menu = []
    navs = []
    for index, section in enumerate(catalog["sections"]):
        current = ' aria-current="page"' if index == 0 else ""
        menu.append(
            f'<a href="#{_esc(section["id"])}" data-section="{_esc(section["id"])}"{current}>{_esc(section["label"])}</a>'
        )
        hidden = "" if index == 0 else " hidden"
        blocks = []
        for author, chunks in _author_chunks(section["groups"]):
            parts = [f'<p class="nav-author">{_esc(author)}</p>']
            for group in chunks:
                if group.get("date"):
                    parts.append(f'<p class="nav-date">{_esc(group["date"])}</p>')
                series = group.get("series")
                articles = group.get("articles") or []
                if series:
                    parts.append(
                        '<button class="nav-series" type="button" aria-expanded="true" '
                        f'aria-controls="{_esc(series["id"])}" data-href="{_esc(series["href"])}">'
                        f'{_esc(series["title"])}</button>'
                    )
                    links = "\n".join(_nav_article(article) for article in articles)
                    parts.append(f'<div class="nav-days is-open" id="{_esc(series["id"])}">\n{links}\n</div>')
                elif articles:
                    parts.extend(_nav_article(article) for article in articles)
                else:
                    parts.append('<p class="nav-empty">Articles will appear here.</p>')
            blocks.append('<div class="nav-group">\n' + "\n".join(parts) + "\n</div>")
        navs.append(
            f'<nav class="shell-nav" data-section="{_esc(section["id"])}" aria-label="Articles by author"{hidden}>\n'
            + "\n".join(blocks)
            + "\n</nav>"
        )
    home = catalog["sections"][0]["start"]
    starts_json = json.dumps(starts, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(catalog["title"])}</title>
  <link rel="icon" href="{_esc(catalog["logo"])}">
  <link rel="stylesheet" href="css/site.css">
  <link rel="stylesheet" href="css/shell.css">
</head>
<body class="shell">
  <header class="shell-top">
    <a class="shell-brand" href="#home">
      <img src="{_esc(catalog["logo"])}" alt="">
      <span>{_esc(catalog["brand"])}</span>
    </a>
    <nav class="shell-menu" aria-label="Sections">
      {"".join(menu)}
    </nav>
    <button class="shell-nav-toggle" type="button" aria-expanded="false" aria-controls="shell-body">Articles</button>
  </header>
  <div class="shell-body" id="shell-body">
    {"".join(navs)}
    <div class="shell-read">
      <iframe id="read" name="read" title="Reading" src="{_esc(home)}"></iframe>
    </div>
  </div>
  <script>window.SHELL_SECTIONS = {starts_json};</script>
  <script src="shell.js"></script>
</body>
</html>
"""


def _document(lang: str, title: str, prefix: str, inner: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="{_esc(lang)}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(title)}</title>
  <link rel="stylesheet" href="{prefix}css/site.css">
  <link rel="stylesheet" href="{prefix}css/shell.css">
</head>
<body>
  <div class="site-wrap">
    <p class="pssm-back-home"><a href="{prefix or "./"}">Self Knowledge</a></p>
{inner}
  </div>
</body>
</html>
"""


def _by(meta: dict, catalog: dict) -> tuple[dict, dict]:
    block = catalog["chrome"][meta["chrome"]]
    lang = meta.get("lang") or "en"
    voice = dict(block["by"].get(lang) or block["by"]["en"])
    if meta.get("author_detail"):
        voice["author_detail"] = meta["author_detail"]
    return voice, block


def _header(prefix: str, voice: dict, block: dict, links: list[tuple[str, str]]) -> str:
    nav = ""
    if links:
        anchors = "\n        ".join(f'<a href="{_esc(href)}">{_esc(label)}</a>' for href, label in links)
        nav = f"\n      <nav>\n        {anchors}\n      </nav>"
    return f"""    <header class="site-header">
      <a class="site-brand" href="index.html">
        <img src="{prefix}{_esc(block["image"])}" alt="{_esc(block["alt"])}">
        <span class="brand-text">{_esc(voice["series_title"])}
        <span>{_esc(voice["series_by"])}</span></span>
      </a>{nav}
    </header>"""


def _reading(page: dict, catalog: dict) -> str:
    meta = page["meta"]
    voice, block = _by(meta, catalog)
    rel = meta["rel"]
    prefix = _prefix(rel)
    folder = str(Path(rel).parent.as_posix())
    lang = meta.get("lang") or "en"
    links = _lang_links(meta, catalog, folder)
    parts = [_header(prefix, voice, block, links)]
    if meta.get("day"):
        parts.append(_day_strip(meta, catalog, folder))
    eyebrow = f'\n    <p class="eyebrow">{_esc(meta["eyebrow"])}</p>' if meta.get("eyebrow") else ""
    when = f'\n    <p class="reading-date">{_esc(meta["date"])}</p>' if meta.get("date") else ""
    footer = f'\n    <footer class="site-footer">{_esc(voice["footer"])}</footer>' if voice.get("footer") else ""
    parts.append(
        f"""    <article class="post-card">
    <div class="author-row">
      <img src="{prefix}{_esc(block["image"])}" alt="{_esc(block["alt"])}">
      <div class="author-info">
        <strong>{_esc(voice["author_name"])}</strong>
        <span>{_esc(voice["author_detail"])}</span>
      </div>{_reading_lang_nav(meta, catalog, folder)}
    </div>{when}{eyebrow}
    <h1>{_esc(meta["h1"])}</h1>
    {page["body"]}
    </article>"""
    )
    if meta.get("day"):
        parts.append(_pager(meta, catalog, folder))
    if footer:
        parts.append(footer.lstrip("\n"))
    return _document(lang, meta.get("title") or meta["h1"], prefix, "\n".join(parts))


def _reading_lang_nav(meta: dict, catalog: dict, folder: str) -> str:
    """Language switch for a single reading. Day pages keep their own header links."""
    if meta.get("day"):
        return ""
    stem = re.sub(r"-(te|kn)$", "", Path(meta["rel"]).stem)
    current = meta.get("lang") or "en"
    anchors = []
    for item in catalog["languages"]:
        name = f"{stem}{item['suffix']}.html"
        if not _exists(f"{folder}/{name}"):
            continue
        mark = ' aria-current="page"' if item["id"] == current else ""
        anchors.append(f'<a href="{_esc(name)}"{mark}>{_esc(item["label"])}</a>')
    if len(anchors) < 2:
        return ""
    return f"""
      <nav aria-label="Language">
        {"\n        ".join(anchors)}
      </nav>"""


def _lang_links(meta: dict, catalog: dict, folder: str) -> list[tuple[str, str]]:
    voice, _block = _by(meta, catalog)
    links = []
    if voice.get("programme"):
        links.append(("index.html", voice["programme"]))
    day = meta.get("day")
    if not day:
        return links
    lang = meta.get("lang") or "en"
    wanted = []
    if lang == "te":
        wanted = ["en"]
    elif lang == "kn":
        wanted = ["en", "te"]
    labels = {item["id"]: item["label"] for item in catalog["languages"]}
    for other in wanted:
        name = _day_name(int(day), other, catalog)
        if _exists(f"{folder}/{name}"):
            links.append((name, labels[other]))
    return links


def _day_strip(meta: dict, catalog: dict, folder: str) -> str:
    lang = meta.get("lang") or "en"
    current = int(meta["day"])
    links = []
    for day in range(1, 10):
        name = _day_name(day, lang, catalog)
        if not _exists(f"{folder}/{name}"):
            name = _day_name(day, "en", catalog)
        mark = ' class="is-current"' if day == current else ""
        links.append(f'<a href="{_esc(name)}"{mark}>{day}</a>')
    return f'    <nav class="day-strip" aria-label="Days">\n      ' + "\n      ".join(links) + "\n    </nav>"


def _pager(meta: dict, catalog: dict, folder: str) -> str:
    voice, _block = _by(meta, catalog)
    lang = meta.get("lang") or "en"
    day = int(meta["day"])
    word = voice.get("day") or "Day"
    if day <= 1:
        previous = f'<span>{_esc(voice.get("prev_first") or "← Previous")}</span>'
    else:
        name = _day_name(day - 1, lang, catalog)
        if not _exists(f"{folder}/{name}"):
            name = _day_name(day - 1, "en", catalog)
        previous = f'<a href="{_esc(name)}">← {_esc(word)} {day - 1}</a>'
    if day >= 9:
        nxt = f'<a href="index.html">{_esc(voice.get("programme") or "Programme")} →</a>'
    else:
        name = _day_name(day + 1, lang, catalog)
        if not _exists(f"{folder}/{name}"):
            name = _day_name(day + 1, "en", catalog)
        nxt = f'<a href="{_esc(name)}">{_esc(word)} {day + 1} →</a>'
    return f'    <nav class="pager">\n      {previous}\n      {nxt}\n    </nav>'


def _series(rel: str, catalog: dict, series: dict) -> str:
    block = catalog["chrome"][series["chrome"]]
    voice = block["by"]["en"]
    prefix = _prefix(rel)
    intro_path = CONTENT / block["intro"]
    intro = intro_path.read_text(encoding="utf-8").strip() if intro_path.is_file() else ""
    folder = str(Path(rel).parent.as_posix())
    items = []
    for day in range(1, 10):
        english = _day_name(day, "en", catalog)
        page = _load_fragment(f"{folder}/{english}")
        subtitle = page["meta"]["h1"] if page else ""
        langs = []
        for item in catalog["languages"]:
            name = _day_name(day, item["id"], catalog)
            if _exists(f"{folder}/{name}"):
                langs.append(f'<a href="{_esc(name)}">{_esc(item["label"])}</a>')
        items.append(
            f"""        <li>
          <div class="day-item">
            <a class="day-main" href="{_esc(english)}">
              <strong>{_esc(voice["day"])} {day}</strong>
              <em>{_esc(subtitle)}</em>
            </a>
            <div class="day-langs">
              {"".join(langs)}
            </div>
          </div>
        </li>"""
        )
    youtube = ""
    if block.get("youtube"):
        youtube = (
            f'<br>\n    <a href="{_esc(block["youtube"])}" target="_blank" rel="noopener">'
            f'{_esc(block.get("youtube_label") or block["youtube"])}</a>'
        )
    inner = f"""{_header(prefix, voice, block, [("index.html", voice["programme"])])}
    <div class="hub-card">
      <h1>{_esc(block["h1"])}</h1>
      {intro}
      <p class="week-label">{_esc(block["week_label"])}</p>
      <ul class="day-list">
{chr(10).join(items)}
      </ul>
    </div>
    <footer class="site-footer">{_esc(voice["footer"])}{youtube}</footer>"""
    return _document("en", block.get("index_title") or voice["series_title"], prefix, inner)


def _tools(rel: str) -> str:
    prefix = _prefix(rel)
    inner = f"""    <div class="hub-card tool-card">
      <h1>Format / Beautify a reading</h1>
      <p class="lede">Format keeps every word. Beautify shapes a Kindle reading or blurb. Check languages to download.</p>
      <form class="tool-form" id="beautify">
        <div class="tool-grid">
          <div class="tool-field tool-field--file">
            <label for="captions-file">Captions (.txt)</label>
            <input id="captions-file" name="captions" type="file" accept=".txt,text/plain">
          </div>
          <div class="tool-field tool-field--speaker">
            <label for="speaker-only">Speaker only <span class="tool-hint">optional</span></label>
            <input id="speaker-only" name="speaker" type="text" placeholder="e.g. Dr. Lakshmi Newton">
          </div>
          <fieldset class="tool-field tool-langs">
            <legend>Languages <span class="tool-hint">Beautify</span></legend>
            <div class="tool-checks">
              <label class="tool-check" for="lang-original">
                <input id="lang-original" name="lang" type="checkbox" value="original" checked>
                <span>Original</span>
              </label>
              <label class="tool-check" for="lang-en">
                <input id="lang-en" name="lang" type="checkbox" value="en">
                <span>English</span>
              </label>
              <label class="tool-check" for="lang-hi">
                <input id="lang-hi" name="lang" type="checkbox" value="hi">
                <span>Hindi</span>
              </label>
            </div>
          </fieldset>
          <div class="tool-field tool-field--options">
            <label class="tool-check" for="blurb-content">
              <input id="blurb-content" name="blurb" type="checkbox">
              <span>Blurb</span>
            </label>
            <div class="tool-words">
              <label for="word-limit">Word limit <span class="tool-hint">empty = full</span></label>
              <input id="word-limit" name="words" type="number" min="50" max="20000" step="50" value="2500" placeholder="No hard cap">
            </div>
          </div>
          <div class="tool-field tool-field--actions">
            <div class="tool-actions tool-actions--prepare">
              <button type="button" class="tool-secondary" id="format-btn">Format the reading</button>
              <button type="button" id="beautify-btn">Beautify</button>
            </div>
            <p class="tool-status" id="tool-status" role="status"></p>
          </div>
        </div>
      </form>
    </div>
    <script src="{prefix}tools.js"></script>"""
    return _document("en", "Tools · Self Knowledge", prefix, inner)



def _nav_article(article: dict) -> str:
    also = article.get("also") or []
    extra = f' data-also="{_esc(" ".join(also))}"' if also else ""
    return (
        f'<a class="nav-article" href="{_esc(article["href"])}"{extra}>'
        f'{_esc(article["label"])}</a>'
    )


def _article_href(from_rel: str, href: str) -> str:
    return Path(os.path.relpath(href, Path(from_rel).parent)).as_posix()


def _author_chunks(groups: list[dict]) -> list[tuple[str, list[dict]]]:
    """Keep site.json date groups, but show each author once in menus/hubs."""
    chunks: list[tuple[str, list[dict]]] = []
    for group in groups:
        author = group.get("author") or ""
        if chunks and chunks[-1][0] == author:
            chunks[-1][1].append(group)
        else:
            chunks.append((author, [group]))
    return chunks


def _hub(rel: str, catalog: dict, section: dict) -> str:
    prefix = _prefix(rel)
    groups = []
    for author, author_groups in _author_chunks(section["groups"]):
        blocks = [f"      <h2>{_esc(author)}</h2>"]
        for group in author_groups:
            if group.get("date"):
                blocks.append(f'      <p class="reading-date">{_esc(group["date"])}</p>')
            articles = group.get("articles") or []
            if articles:
                blocks.extend(
                    f'      <p><a href="{_esc(_article_href(rel, article["href"]))}">{_esc(article["label"])}</a></p>'
                    for article in articles
                )
            else:
                blocks.append('      <p class="nav-empty">Articles will appear here.</p>')
        groups.append(
            f"""    <section class="reading-group">
{chr(10).join(blocks)}
    </section>"""
        )
    listing = "\n".join(groups)
    inner = f"""    <div class="hub-card">
      <h1>{_esc(section.get("hub_title") or section["label"])}</h1>
      <p class="lede">{_esc(section.get("hub_lede") or "")}</p>
      {listing}
    </div>"""
    title = f'{section.get("hub_title") or section["label"]} · Self Knowledge'
    return _document("en", title, prefix, inner)


def published_paths() -> list[str]:
    catalog = load_catalog()
    paths = ["index.html"]
    for section in catalog["sections"]:
        start = section["start"] if section["start"].endswith("/") else section["start"] + "/"
        paths.append(start + "index.html")
    paths.extend(_pages())
    return paths
