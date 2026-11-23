#!/usr/bin/env python3
"""Copy the 9-day Anapanasati pages with their original parchment styling."""

from __future__ import annotations

import shutil
from pathlib import Path

SRC = Path(
    r"c:\Users\dhana\GitHub\awakening-the-wisdom-within-1"
    r"\Session-Schedules\9-Day-Anapanasati-Meditation-Spiritual-Seed"
)
CSS_SRC = SRC.parents[1] / "css" / "site.css"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "readings" / "9-day-anapanasati"
CSS_OUT = ROOT / "docs" / "css" / "site.css"

BACK = (
    '<div class="site-wrap">\n'
    '    <p class="pssm-back-home"><a href="../../">Self Knowledge</a></p>'
)


def main() -> None:
    if not SRC.is_dir():
        raise SystemExit(f"Missing source series: {SRC}")
    if not CSS_SRC.is_file():
        raise SystemExit(f"Missing stylesheet: {CSS_SRC}")
    OUT.mkdir(parents=True, exist_ok=True)
    CSS_OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CSS_SRC, CSS_OUT)
    count = 0
    for src in sorted(SRC.glob("*.html")):
        text = src.read_text(encoding="utf-8")
        if 'class="site-wrap"' in text and "pssm-back-home" not in text:
            text = text.replace('<div class="site-wrap">', BACK, 1)
        style = '<link rel="stylesheet" href="../../css/site.css">'
        shell = style + '\n  <link rel="stylesheet" href="../../css/shell.css">'
        if style in text and "css/shell.css" not in text:
            text = text.replace(style, shell, 1)
        text = text.replace(
            "https://yt3.googleusercontent.com/oIT20Ynxjv5D0-qqWHoLmJWZKmx9vhPKAIgMXIy22cQDY9fGj-tF2TfWmiz-Nw9GabJvP8It=s240-c-k-c0x00ffffff-no-rj",
            "../../assets/spiritual-seed.jpg",
        )
        (OUT / src.name).write_text(text, encoding="utf-8", newline="\n")
        count += 1
        print(f"  {src.name}")
    print(f"Wrote {count} pages and {CSS_OUT}")


if __name__ == "__main__":
    main()
