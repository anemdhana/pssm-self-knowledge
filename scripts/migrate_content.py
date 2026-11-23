"""One-time move: full HTML pages become content fragments plus static files."""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pages import split_legacy_html, write_fragment  # noqa: E402

DOCS = ROOT / "docs"
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
SERIES = "readings/9-day-anapanasati"
DEFAULT_DETAIL = {
    "en": "Anapanasati under Bramharshi Premnath Sir · since 2016 · PSSM",
    "te": "బ్రహ్మర్షి ప్రేమనాథ్ సార్ మార్గదర్శకత్వంలో అనాపానసతి · 2016 నుండి · PSSM",
    "kn": "ಬ್ರಹ್ಮರ್ಷಿ ಪ್ರೇಮನಾಥ್ ಸರ್ ಮಾರ್ಗದರ್ಶನದಲ್ಲಿ ಅನಾಪಾನಸತಿ · 2016ರಿಂದ · PSSM",
}


def reading(src: Path, rel: str, chrome: str) -> None:
    text = src.read_text(encoding="utf-8")
    pulled = split_legacy_html(text)
    lang = pulled["lang"]
    match = re.search(r"day-(\d+)", src.name)
    meta = {
        "layout": "reading",
        "chrome": chrome,
        "lang": lang,
        "title": pulled["title"],
        "h1": pulled["h1"],
    }
    if pulled["eyebrow"]:
        meta["eyebrow"] = pulled["eyebrow"]
    if match:
        meta["day"] = int(match.group(1))
    detail = pulled["author_detail"]
    if detail and detail != DEFAULT_DETAIL.get(lang):
        meta["author_detail"] = detail
    write_fragment(CONTENT / rel, meta, pulled["body"])
    print(rel)


def intro() -> None:
    text = (DOCS / SERIES / "index.html").read_text(encoding="utf-8")
    match = re.search(r'(<p class="lede">.*?</div>\s*)\s*<p class="week-label">', text, re.S)
    if not match:
        raise SystemExit("Could not find the programme introduction")
    body = match.group(1).strip()
    body = body.replace(
        '<span style="font-size:13px;color:var(--ink-muted)">',
        "<span>",
    )
    dest = CONTENT / SERIES / "_intro.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body + "\n", encoding="utf-8", newline="\n")
    print(SERIES + "/_intro.html")


def static_files() -> None:
    for name in ("site.css", "shell.css"):
        dest = STATIC / "css" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DOCS / "css" / name, dest)
    assets = STATIC / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for path in (DOCS / "assets").iterdir():
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            shutil.copyfile(path, assets / path.name)
    shutil.copyfile(DOCS / "shell.js", STATIC / "shell.js")


def main() -> None:
    for path in sorted((DOCS / SERIES).glob("day-*.html")):
        reading(path, f"{SERIES}/{path.name}", "anapanasati")
    reading(DOCS / SERIES / "vegetarian-living.html", f"{SERIES}/vegetarian-living.html", "anapanasati")
    reading(
        DOCS / "readings/brahmarshi-patriji/cosmic-energy.html",
        "readings/brahmarshi-patriji/cosmic-energy.html",
        "patriji",
    )
    intro()
    static_files()


if __name__ == "__main__":
    main()
