#!/usr/bin/env python3
"""Regenerate the static `data.json` snapshot from Anki.

Run this on the VM (where AnkiConnect lives), then commit + push so the
GitHub Pages site reflects the latest deck. Only rewrites the file when the
word data actually changed, so a no-op refresh doesn't produce a commit.

    python3 generate.py
"""

from __future__ import annotations

import json
from pathlib import Path

from server import build_data

ROOT = Path(__file__).resolve().parent


def _without_meta(data: dict) -> dict:
    return {k: v for k, v in data.items() if k != "generated_at"}


if __name__ == "__main__":
    data = build_data()
    out = ROOT / "data.json"
    existing = {}
    if out.exists():
        existing = json.loads(out.read_text(encoding="utf-8"))
    if _without_meta(existing) == _without_meta(data):
        print("no change — data.json up to date")
    else:
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {out} — {data['total_words']} words, overall health {data['overall_health']}")
