#!/usr/bin/env python3
"""Print the Python version and exit 1 if it is older than 3.10."""

from __future__ import annotations

import sys


def main() -> int:
    v = sys.version_info
    print(f"  Python {v.major}.{v.minor}.{v.micro}")
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print("  ERROR: Python 3.10 or newer is required.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
