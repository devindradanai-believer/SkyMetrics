#!/usr/bin/env python3
"""
SkyMetrics -- Aircraft Performance Analysis Tool
Entry point. Run with: python main.py
"""

import sys
import traceback

from src.gui.app import run


def main() -> int:
    try:
        run()
    except Exception:
        # Never let a raw traceback be the last thing a user sees; log
        # it and print a short, non-technical message instead.
        print("SkyMetrics encountered a fatal error and had to close.")
        print("Technical details have been printed below for debugging:")
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
