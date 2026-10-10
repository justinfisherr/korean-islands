#!/usr/bin/env python3
"""Korean Islands — live Anki progress visualizer (read-only).

Serves the static site plus a JSON API built fresh from AnkiConnect on every
request, so the map always reflects the current state of the Anki deck.

Run:  python3 server.py  →  http://localhost:8787
"""

from __future__ import annotations

import json
import math
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ANKI_URL = "http://127.0.0.1:8765"
DECK = "Korean-lingq"
PORT = 8787

STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


def anki(action: str, **params):
    req = urllib.request.Request(
        ANKI_URL,
        data=json.dumps({"action": action, "version": 6, "params": params}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.load(resp)
    if payload.get("error") is not None:
        raise RuntimeError(f"AnkiConnect {action}: {payload['error']}")
    return payload["result"]


def word_health(card: dict) -> tuple[str, float]:
    ctype = card.get("type", 0)
    if ctype == 0:  # new
        return "new", 0.15
    if ctype == 1:  # learning / relearning
        return "learning", 0.35
    interval = max(card.get("interval", 0), 0)
    # review: grow toward 1.0 on a log curve up to ~6 months
    h = min(1.0, 0.4 + 0.6 * (math.log(interval + 1) / math.log(181)))
    return "review", round(h, 3)


def build_data() -> dict:
    domains_cfg = json.loads((ROOT / "domains.json").read_text(encoding="utf-8"))
    cards = anki("findCards", query=f"deck:{DECK}")
    cards_info = anki("cardsInfo", cards=cards)

    by_term: dict[str, dict] = {}
    for c in cards_info:
        f = c.get("fields", {})
        term = (f.get("Term") or {}).get("value", "").strip()
        if not term:
            continue
        status, health = word_health(c)
        by_term[term] = {
            "term": term,
            "meaning": (f.get("MeaningEn") or {}).get("value", ""),
            "base_form": (f.get("BaseForm") or {}).get("value", ""),
            "example": (f.get("ExampleKo") or {}).get("value", ""),
            "example_en": (f.get("ExampleEn") or {}).get("value", ""),
            "mnemonic": (f.get("Mnemonic") or {}).get("value", ""),
            "similar": (f.get("SimilarWords") or {}).get("value", ""),
            "status": status,
            "interval_days": c.get("interval", 0) if c.get("type", 0) == 2 else 0,
            "health": health,
        }

    classified: set[str] = set()
    out_domains: list[dict] = []
    for d in domains_cfg["domains"]:
        islands = []
        for isl in d.get("islands", []):
            words = [by_term[t] for t in isl.get("terms", []) if t in by_term]
            classified.update(isl.get("terms", []))
            if not words:
                continue
            size = len(words)
            health = round(sum(w["health"] for w in words) / size, 3)
            islands.append(
                {
                    "id": isl.get("id"),
                    "name": isl.get("name"),
                    "name_native": isl.get("name_native"),
                    "size": size,
                    "health": health,
                    "words": words,
                }
            )
        if islands:
            out_domains.append(
                {
                    "id": d.get("id"),
                    "name": d.get("name"),
                    "name_native": d.get("name_native"),
                    "islands": islands,
                }
            )

    # Any words in Anki but not yet mapped into a domain.
    leftovers = [w for t, w in by_term.items() if t not in classified]
    if leftovers:
        health = round(sum(w["health"] for w in leftovers) / len(leftovers), 3)
        out_domains.append(
            {
                "id": "unmapped",
                "name": "Unmapped",
                "name_native": "기타",
                "islands": [
                    {
                        "id": "unmapped",
                        "name": "Not yet placed",
                        "name_native": "미분류",
                        "size": len(leftovers),
                        "health": health,
                        "words": sorted(leftovers, key=lambda w: w["term"]),
                    }
                ],
            }
        )

    overall = (
        round(sum(w["health"] for w in by_term.values()) / len(by_term), 3)
        if by_term
        else 0.0
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deck": DECK,
        "total_words": len(by_term),
        "overall_health": overall,
        "domains": out_domains,
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/api/data", "/data.json"):
            self._json()
            return
        if path == "/":
            path = "/index.html"
        self._static(path)

    def _json(self):
        try:
            data = build_data()
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
        except Exception as exc:  # noqa: BLE001
            body = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, path: str):
        target = (ROOT / path.lstrip("/")).resolve()
        if not str(target).startswith(str(ROOT)) or not target.is_file():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")
            return
        body = target.read_bytes()
        ctype = STATIC_TYPES.get(target.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # noqa: ARG002
        pass


def main() -> None:
    print(f"Korean Islands → http://localhost:{PORT}")
    print(f"Reading live from AnkiConnect ({ANKI_URL}), deck '{DECK}'")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
