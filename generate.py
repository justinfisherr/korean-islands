#!/usr/bin/env python3
"""Regenerate the static `data.json` snapshot from Anki.

Run this on the VM (where AnkiConnect lives), then commit + push so the
GitHub Pages site reflects the latest deck:

    python3 generate.py && git add data.json && git commit -m "refresh islands" && git push
"""

from __future__ import annotations

import json
from pathlib import Path

from server import build_data

ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    data = build_data()
    out = ROOT / "data.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out} — {data['total_words']} words, overall health {data['overall_health']}")
