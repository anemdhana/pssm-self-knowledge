#!/usr/bin/env python3
"""Write the static site used by GitHub Pages."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pages import build  # noqa: E402


def main() -> None:
    out = ROOT / "_site"
    if len(sys.argv) == 3 and sys.argv[1] == "--out":
        out = Path(sys.argv[2])
    count = build(out)
    print(f"Wrote {count} pages to {out}")


if __name__ == "__main__":
    main()
