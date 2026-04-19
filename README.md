# Song Map

An explorer for Ukrainian folk songs. Pick a region on the map, drill into
the singers who lived there, read their songs, follow recommendations to
similar songs and similar singers. Filter by theme or emotion along the
way.

It's a static-ish web app — a small Python preprocessing step turns the
corpus CSVs into JSON that the Next.js frontend reads directly. No server,
no database.

## Run it

You need Python 3 (with `pandas` and `shapely`) and Node 20+.

```bash
# 1. Build the data bundle (reads the CSVs in the repo root, writes JSON
#    and a GeoJSON to public/data/)
py -3 -m pip install pandas shapely
py -3 scripts/prepare_data.py

# 2. Install and start the dev server
npm install
npm run dev
```

Open http://localhost:3000. Click a region, click a singer, click a song.
Everything else is in the sidebar.

## Where the data comes from

Three CSVs in the repo root, each richer than the last. The pipeline picks
the richest one present:

- `songs_with_recommendations.csv` — adds a `similar_songs` column (ranked
  song-id list). This is the canonical input.
- `songs_with_emotions.csv` — adds `valence` and `arousal` floats.
- `songs_with_themes.csv` — adds a `themes` list and `primary_theme`.

Plus:

- `singers.json` — pre-built singer records, one per `singer_id`, with
  `similar_singers` rankings. Copied to `public/data/` as-is.
- `themes.json` — curated theme list (id, display label, counts). Copied
  through; the pipeline warns if its counts drift from the CSV.

If you're missing emotions or themes, the pipeline falls back: it will
derive valence/arousal from theme priors and just skip what it can't.
Drop a real `songs_with_emotions.csv` in when you have one and re-run.

## Map geography

The map shows **seven ethnographic regions**, not oblasts. The source is
geoBoundaries ADM1 (24 oblast polygons). `scripts/prepare_data.py` fetches
it, runs `shapely.ops.unary_union` per ethno group (`OBLAST_TO_ETHNO` is
hand-mapped), cleans slivers, and writes
`public/data/ukraine_ethno_regions.geojson`.

Singer data stays at oblast level though — an oblast-level grouping is
more informative for "which Poltava kobzar is this". The frontend bridges
the two via `src/lib/oblasts.ts`, which mirrors the same
`OBLAST_TO_ETHNO` table.

## Code shape

```
scripts/prepare_data.py     # CSV → /public/data/*.json + geojson
public/data/                # what the app actually loads
src/app/page.tsx            # layout, filter state, nav stack, URL hash
src/components/Map.tsx      # MapLibre wrapper
src/components/ThemesPanel.tsx      # left sidebar, top
src/components/EmotionSliders.tsx   # left sidebar, bottom
src/components/RightPanel.tsx       # dispatches to one of:
src/components/RegionView.tsx
src/components/SingerView.tsx
src/components/SongView.tsx
src/lib/recommendations.ts  # filter helpers, unknown-bucket check
src/lib/range-slider.tsx    # dual-handle primitive
src/lib/density-scale.ts    # shared sqrt color ramp
```

The right-panel views are three different components; `RightPanel`
mounts one at a time based on the top of the nav stack.

## Filtering model

Two independent filters combine via AND:

- **Themes** (OR within the set): a song passes if it has any selected
  theme.
- **Emotion** (range): a song passes if its `valence` is inside the tone
  range and `arousal` is inside the energy range.

When either is active, the map recolors by filtered song counts per
region, the theme counts update to co-occurrence, and the right-panel
singer/song lists narrow. Nothing is ever _hidden_ from recommendations —
similar-songs and similar-singers still resolve; they're just re-ordered
to put filter-matching ones first, and fall back to the unfiltered top 5
if the filter would leave fewer than three.

## Navigation

The right panel has a 10-entry stack. Clicking a region resets it;
clicking a similar singer or similar song pushes onto it. The URL hash
mirrors the top entry (`#/singer/poltava--ostap-vereai`), so you can
share or refresh into any view.

## What's not in here yet

Estonia. The pipeline is country-agnostic; the Estonian tab shows a
placeholder until we have data.
