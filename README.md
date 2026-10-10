# Korean Islands 🌱

A map of your Korean vocabulary from Anki, drawn as an archipelago. Deployed as a static GitHub Pages site.

Each **island** groups words that fit a shared context (eating, shopping, feelings…). Islands live inside a **domain** (Food, Shopping, Everyday Life…). The bigger an island, the more words live there; the greener and taller its plants, the healthier those cards are in Anki.

## How it works

- `domains.json` maps Korean words into domains → islands (the only file you hand-edit).
- `generate.py` reads your Anki deck (`Korean-lingq`) through **AnkiConnect** and writes `data.json`.
- `index.html` renders `data.json` — pure static, no build, no backend on GitHub Pages.
- `server.py` is an optional **live** mode for local dev (serves `data.json` fresh from Anki on each request).

Word health comes from Anki's card state: new (🌱) → learning (🌿) → review, growing toward a tree (🌳) as the interval lengthens.

## Refresh the deployed site

On the VM (where Anki lives):

```bash
cd ~/Projects/korean-islands
python3 generate.py
git add data.json && git commit -m "refresh islands" && git push
```

## Local live mode (optional)

```bash
python3 server.py        # http://localhost:8787 — data.json served live from Anki
```

## Classifying new words

When `/anki` adds a word, drop its `term` into the right island's `terms` list in `domains.json`, then run the refresh above. Anything unmapped shows up under an **Unmapped** domain so gaps are visible.
