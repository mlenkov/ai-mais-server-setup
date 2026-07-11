#!/usr/bin/env python3
"""Entry point for AI Mais Server Setup."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.main import main

if __name__ == "__main__":
    main()
