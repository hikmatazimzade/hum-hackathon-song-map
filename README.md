# Song Map

Song Map is an interactive platform for the Ukrainian folk song archive. The aim is
to explore the corpus geographically, then drill into singers, themes,
and individual songs, with recommendations linking to related work.
The app is static: a Python preprocessing step produces JSON from the
source CSVs, and the Next.js frontend reads those files directly. No
server, no database.

## Running it

Node 20+ is required. The generated JSON in `public/data/` is
committed, so the frontend runs on its own:

```
npm install
npm run dev
```

Open http://localhost:3000.

## Source data

Three song CSVs live in the repo root. They share a base schema and
add progressively more annotation:

- `songs_with_themes.csv` — a themes list and primary theme per song.
- `songs_with_emotions.csv` — adds valence and arousal floats, both
  in the range [-1, 1].
- `songs_with_recommendations.csv` — adds `similar_songs`, a ranked
  list of 10 song-ids per song.

The pipeline uses the richest file present and falls back when fields
are missing.

Two supporting files:

- `singers.json` — one record per `singer_id` with role, region,
  `song_ids`, and a `similar_singers` ranking.
- `themes.json` — the 12 theme entries (id, display label, total
  count, primary count).

Both are copied to `public/data/` without modification.

## Themes

Themes are assigned upstream. The pipeline reads them; it doesn't
re-derive them. Each song has up to three themes from a fixed
vocabulary of 12: love, family, wedding, cossack_life, captivity,
death, labor_hardship, military_service, ritual_seasonal, faith,
nature, humor. The first theme in the list is the primary.

The themes sidebar shows all 12 with a density bar scaled by
square-root of the live count. Selecting one or more applies an OR
filter: a song passes if it has any of the selected themes. The
count beside each theme updates to reflect co-occurrence with the
current filter.

## Emotion

Each song carries a valence (sad ↔ happy) and arousal (calm ↔
intense). When the source CSV lacks these, the pipeline derives them
from the theme list:

- Each theme has a hand-picked `(valence, arousal)` prior (e.g.
  `captivity ≈ (-0.80, +0.55)`, `humor ≈ (+0.75, +0.70)`).
- A song's value is a weighted average: 70% on the primary theme,
  30% on the mean of the remaining themes.
- A deterministic hash-based jitter is added so songs with identical
  theme sets don't stack on a single point.

The emotion sidebar has two dual-handle range sliders. A song passes
the emotion filter when its valence is inside the tone range and
its arousal inside the energy range.

## Filter composition

Theme and emotion filters combine with AND. A song is visible when:

- it has at least one selected theme, or no themes are selected, and
- its valence is within the tone range, and
- its arousal is within the energy range.

When either filter is active, the map recolors by filtered per-region
counts, the theme bars recompute co-occurrence, and the right-panel
lists hide entries with no visible songs.

## Recommendations

`similar_songs` (per song) and `similar_singers` (per singer) are
pre-computed upstream and shipped inside the JSON. The frontend
doesn't compute similarity; it resolves ids, filters, and displays.

For each recommendation list:

1. Resolve the ranked ids to full records.
2. Drop unknown-attribution buckets (see below).
3. Apply the active theme and emotion filters.
4. Take the top five.
5. If the filter leaves fewer than three, fall back to the
   unfiltered top five and label the section
   `(showing without filters)`.

Unknown buckets are singer records representing songs whose
respondent wasn't recorded. Their `singer_id` looks like
`poltava--` or `vinnytska--unknown` and their `name` is empty. They
are never surfaced as clickable recommendations. In a region's
singer list they collapse into a single
"+ N songs without singer attribution" link that opens the bucket
itself.

## The map

The map shows seven ethnographic regions rather than the 24 modern
oblasts: Polissia, Volyn, Halychyna, Podillia, Naddniprianshchyna,
Slobozhanshchyna, Pivden. Folk song traditions follow these
historical regions more closely than administrative borders.

The pipeline pulls oblast polygons from the geoBoundaries ADM1
dataset, groups them with `OBLAST_TO_ETHNO` in
`scripts/prepare_data.py`, dissolves each group with
`shapely.ops.unary_union`, cleans slivers, and writes
`public/data/ukraine_ethno_regions.geojson`.

The frontend mirrors `OBLAST_TO_ETHNO` in `src/lib/oblasts.ts`. The
two tables need to stay in sync. Singers keep their oblast in the
UI because "Poltava" is more informative than "Naddniprianshchyna"
on a singer card; the ethnographic region is used only to group
singers onto the map.

## Navigation

The right panel keeps a back stack of up to 10 entries. Clicking a
region on the map replaces the stack. Clicking a similar singer or
similar song pushes onto it. The Back link pops one entry.

The URL hash tracks the top of the stack:

```
#/region/Naddniprianshchyna
#/singer/poltava--ostap-vereai
#/song/<song-id>
```

Refreshing or sharing the URL lands directly in that view.

## Possible extensions

- **Estonia.** The pipeline is country-agnostic and the layout has
  an Estonia tab. Adding equivalent Estonian CSVs, a region mapping,
  and a GeoJSON source would wire up the rest.
- **Real search.** The header search input is currently a
  placeholder. Indexing titles, lyrics, and singer names against the
  in-memory data is straightforward.
- **Audio.** No playback yet. If audio becomes available per song,
  each `SongView` can embed a player alongside the lyrics.
- **Theme and emotion derivation from text.** Themes and emotion
  currently arrive pre-computed. Moving that step into the pipeline
  would remove the dependency on the annotated CSVs.
- **Singer biographies.** Linking biographical text and photographs
  for notable performers (especially kobzari and lirnyky) would add
  depth to `SingerView`.
- **Lyrics translation.** An English gloss beside the Ukrainian text
  would make the archive accessible to a wider audience.
