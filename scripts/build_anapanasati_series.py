#!/usr/bin/env python3
"""Refresh Anapanasati reading fragments from the source series.

The shared layout stays here. This copies only the teaching text, plus site.css.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

SRC = Path(
    r"c:\Users\dhana\GitHub\awakening-the-wisdom-within-1"
    r"\Session-Schedules\9-Day-Anapanasati-Meditation-Spiritual-Seed"
)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pages import split_legacy_html, write_fragment  # noqa: E402

CSS_SRC = SRC.parents[1] / "css" / "site.css"
SERIES = "readings/9-day-anapanasati"
OUT = ROOT / "content" / SERIES
CSS_OUT = ROOT / "static" / "css" / "site.css"
PORTRAIT = "../../assets/spiritual-seed.jpg"
YOUTUBE = (
    "https://yt3.googleusercontent.com/oIT20Ynxjv5D0-qqWHoLmJWZKmx9vhPKAIgMXIy22cQDY9fGj-tF2TfWmiz-Nw9GabJvP8It"
    "=s240-c-k-c0x00ffffff-no-rj"
)
DEFAULT_DETAIL = {
    "en": "Anapanasati under Bramharshi Premnath Sir · since 2016 · PSSM",
    "te": "బ్రహ్మర్షి ప్రేమనాథ్ సార్ మార్గదర్శకత్వంలో అనాపానసతి · 2016 నుండి · PSSM",
    "kn": "ಬ್ರಹ್ಮರ್ಷಿ ಪ್ರೇಮನಾಥ್ ಸರ್ ಮಾರ್ಗದರ್ಶನದಲ್ಲಿ ಅನಾಪಾನಸತಿ · 2016ರಿಂದ · PSSM",
}


def fragment(src: Path) -> None:
    text = src.read_text(encoding="utf-8").replace(YOUTUBE, PORTRAIT)
    pulled = split_legacy_html(text)
    match = re.search(r"day-(\d+)", src.name)
    meta = {
        "layout": "reading",
        "chrome": "anapanasati",
        "lang": pulled["lang"],
        "title": pulled["title"],
        "h1": pulled["h1"],
    }
    if pulled["eyebrow"]:
        meta["eyebrow"] = pulled["eyebrow"]
    if match:
        meta["day"] = int(match.group(1))
    detail = pulled["author_detail"]
    if detail and detail != DEFAULT_DETAIL.get(pulled["lang"]):
        meta["author_detail"] = detail
    write_fragment(OUT / src.name, meta, pulled["body"])


def main() -> None:
    if not SRC.is_dir():
        raise SystemExit(f"Missing source series: {SRC}")
    if not CSS_SRC.is_file():
        raise SystemExit(f"Missing stylesheet: {CSS_SRC}")
    CSS_OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CSS_SRC, CSS_OUT)
    count = 0
    for src in sorted(SRC.glob("day-*.html")):
        fragment(src)
        count += 1
    vegetarian = SRC / "vegetarian-living.html"
    if vegetarian.is_file():
        fragment(vegetarian)
        count += 1
    print(f"Wrote {count} reading fragments and {CSS_OUT}")


if __name__ == "__main__":
    main()
