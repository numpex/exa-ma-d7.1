#!/usr/bin/env python3
"""Compatibility entry point for the exa-ma-version CLI (Python 3.11+)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exama_version.cli import *  # noqa: F403,E402

if __name__ == "__main__":
    main()
