"""Build the JSON bundle the Song Map frontend loads from /public/data/.

Reads songs_merged.csv and emits:
  public/data/songs.json
  public/data/singers.json
  public/data/regions.json
  public/data/ukraine_oblasts.geojson

Also caches the raw source GeoJSON at public/data/ukraine_raw.geojson.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

import pandas as pd
from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parent.parent
# Input preference, richest first: recommendations CSV → emotions CSV →
# themes CSV. Only the recommendations CSV provides `similar_songs`.
_REC_CSV = ROOT / "songs_with_recommendations.csv"
_EMO_CSV = ROOT / "songs_with_emotions.csv"
_THEMES_CSV = ROOT / "songs_with_themes.csv"
CSV_PATH = (
    _REC_CSV if _REC_CSV.exists()
    else _EMO_CSV if _EMO_CSV.exists()
    else _THEMES_CSV
)
THEMES_SRC = ROOT / "themes.json"
SINGERS_SRC = ROOT / "singers.json"

# Theme → (valence, arousal) priors. Used to derive per-song emotion when
# the raw emotions CSV isn't available. Hand-picked from the brief's
# distribution description (captivity dominates sad+intense, lullaby
# themes sit in happy+calm, etc.).
THEME_EMOTION_PRIORS: dict[str, tuple[float, float]] = {
    "love":              ( 0.50, -0.25),
    "family":            ( 0.35, -0.45),
    "wedding":           ( 0.65,  0.05),
    "cossack_life":      ( 0.10,  0.50),
    "captivity":         (-0.80,  0.55),
    "death":             (-0.65, -0.40),
    "labor_hardship":    (-0.45, -0.30),
    "military_service":  (-0.30,  0.45),
    "ritual_seasonal":   ( 0.30,  0.15),
    "faith":             ( 0.10, -0.60),
    "nature":            ( 0.40, -0.50),
    "humor":             ( 0.75,  0.70),
}
OUT_DIR = ROOT / "public" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

GEOJSON_URL = (
    "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/"
    "gbOpen/UKR/ADM1/geoBoundaries-UKR-ADM1_simplified.geojson"
)
GEOJSON_URL_FALLBACK = (
    "https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/"
    "releaseData/gbOpen/UKR/ADM1/geoBoundaries-UKR-ADM1_simplified.geojson"
)
RAW_GEOJSON_PATH = OUT_DIR / "ukraine_adm1_raw.geojson"

EXCLUDED_REGIONS = {"Unknown"}
PODILLIA_HISTORICAL = "Podillia (historical)"

# Oblast → ethnographic region.
#
# The 16 oblasts with song data (marked * below) came from the brief. The
# other oblasts have ZERO songs but are included so the seven ethnographic
# polygons end up adjacent on the map (no gaps). Assignments follow the
# standard Ukrainian ethnographic tradition.
#
# Hidden from the map (no data, distinct ethno regions): Zakarpattia
# (Transcarpathia), Chernivtsi (Bukovyna), Kyiv City (sits inside Kyiv
# Oblast's donut).
OBLAST_TO_ETHNO: dict[str, str] = {
    # Polissia — northern forest belt
    "Zhytomyr":        "Polissia",           # *
    "Chernihiv":       "Polissia",           # *
    "Rivne":           "Polissia",           #   bridges Volyn ↔ Polissia
    # Volyn — far NW
    "Volyn":           "Volyn",              # *
    # Halychyna — Galicia, western
    "Lviv":            "Halychyna",          # *
    "Ivano-Frankivsk": "Halychyna",          # *
    "Ternopil":        "Halychyna",          #   bridges Halychyna ↔ Podillia
    # Podillia — central-west
    "Vinnytska":       "Podillia",           # *
    "Khmelnytskyi":    "Podillia",           # *
    # Naddniprianshchyna — Dnieper Ukraine, central
    "Kyiv":            "Naddniprianshchyna", # *
    "Poltava":         "Naddniprianshchyna", # *
    "Cherkasy":        "Naddniprianshchyna", # *
    "Dnipropetrovsk":  "Naddniprianshchyna", # *
    "Kirovohrad":      "Naddniprianshchyna", #   bridges to Pivden
    # Slobozhanshchyna — NE
    "Kharkiv":         "Slobozhanshchyna",   # *
    "Sumy":            "Slobozhanshchyna",   # *
    "Luhansk":         "Slobozhanshchyna",
    # Pivden — Black Sea coast, southern steppe + Crimea
    "Mykolaiv":        "Pivden",             # *
    "Kherson":         "Pivden",             # *
    "Crimea":          "Pivden",             # *
    "Odesa":           "Pivden",             #   bridges Podillia ↔ Pivden (NW corner)
    "Zaporizhzhia":    "Pivden",
    "Donetsk":         "Pivden",             #   south steppe; avoids dragging Slobozh miny below 48°
    "Sevastopol":      "Pivden",             #   merged into Crimea's piece
}

# Map from geoBoundaries `shapeName` field to our English oblast name.
# Anything not listed here is not part of any ethnographic region we render
# (Zakarpattia, Chernivtsi, Kyiv City) and gets skipped silently.
SHAPENAME_TO_OBLAST: dict[str, str] = {
    "Vinnytsia Oblast":                "Vinnytska",
    "Volyn Oblast":                    "Volyn",
    "Dnipropetrovsk Oblast":           "Dnipropetrovsk",
    "Donetsk Oblast":                  "Donetsk",
    "Zhytomyr Oblast":                 "Zhytomyr",
    "Zaporizhia Oblast":               "Zaporizhzhia",
    "Ivano-Frankivsk Oblast":          "Ivano-Frankivsk",
    "Kyiv Oblast":                     "Kyiv",         # the larger donut, not the city
    "Kirovohrad Oblast":               "Kirovohrad",
    "Luhansk Oblast":                  "Luhansk",
    "Lviv Oblast":                     "Lviv",
    "Mykolaiv Oblast":                 "Mykolaiv",
    "Odessa Oblast":                   "Odesa",
    "Poltava Oblast":                  "Poltava",
    "Rivne Oblast":                    "Rivne",
    "Sumy Oblast":                     "Sumy",
    "Ternopil Oblast":                 "Ternopil",
    "Kharkiv Oblast":                  "Kharkiv",
    "Kherson Oblast":                  "Kherson",
    "Khmelnytskyi Oblast":             "Khmelnytskyi",
    "Cherkasy Oblast":                 "Cherkasy",
    "Chernihiv Oblast":                "Chernihiv",
    "Autonomous Republic of Crimea":   "Crimea",
    "Sevastopol":                      "Sevastopol",
    # Skipped: "Kyiv" (city), "Zakarpattia Oblast", "Chernivtsi Oblast"
}

# Role prefixes we strip from respondent strings (case-insensitive).
# The spec lists three; we keep that exact set.
ROLE_PREFIXES = ["кобзар", "лірник", "бандурист"]

# Robust Ukrainian-stem match. Each English region name maps to a list of
# lowercased Ukrainian substrings; a geojson feature matches if any stem is
# in its lowercased name:uk / name. This survives minor source variations
# ("Чернігівська" vs "Чернігів. обл." vs "Чернігівщина") where a rigid
# literal-equality match would silently break.
REGION_UK_STEMS: dict[str, list[str]] = {
    "Vinnytska":       ["вінниц"],
    "Volyn":           ["волин"],
    "Dnipropetrovsk":  ["дніпропетров"],
    "Donetsk":         ["донец"],
    "Zhytomyr":        ["житомир"],
    "Zakarpattia":     ["закарпат"],
    "Zaporizhzhia":    ["запоріз"],
    "Ivano-Frankivsk": ["івано-франків", "івано-франк"],
    "Kyiv":            ["київ"],
    "Kirovohrad":      ["кіровоград"],
    "Luhansk":         ["луган"],
    "Lviv":            ["львів"],
    "Mykolaiv":        ["миколаїв"],
    "Odesa":           ["одес"],
    "Poltava":         ["полтав"],
    "Rivne":           ["рівнен", "рівне"],
    "Sumy":            ["сумськ", "сум"],
    "Ternopil":        ["тернопіл"],
    "Kharkiv":         ["харків"],
    "Kherson":         ["херсон"],
    "Khmelnytskyi":    ["хмельниц"],
    "Cherkasy":        ["черкас"],
    "Chernivtsi":      ["чернівец", "чернівц"],
    "Chernihiv":       ["чернігів"],
    "Crimea":          ["автономна республіка крим", "крим"],
    "Sevastopol":      ["севастопол"],
}


def match_region(name_uk: str) -> str | None:
    """Return our English region name for a Ukrainian feature name, or None."""
    if not name_uk:
        return None
    s = name_uk.strip().lower()
    # Longer stems first so "івано-франків" beats the bare "крим" overlap
    # of a hypothetical other name.
    ordered: list[tuple[str, str]] = sorted(
        [(stem, region) for region, stems in REGION_UK_STEMS.items() for stem in stems],
        key=lambda x: -len(x[0]),
    )
    for stem, region in ordered:
        if stem in s:
            # Kyiv disambiguation: match only Kyiv *Oblast*, not the city.
            if region == "Kyiv" and "міст" in s:  # "місто" = city
                continue
            return region
    return None

YEAR_RE = re.compile(r"(1[6-9]\d{2}|20[0-2]\d)")


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\u0400-\u04ff]+", "-", s)
    return s.strip("-") or "x"


def extract_year(raw) -> int | None:
    if pd.isna(raw):
        return None
    m = YEAR_RE.search(str(raw))
    return int(m.group(1)) if m else None


def split_role(respondent) -> tuple[str | None, str | None]:
    """Return (role, normalized_name) stripped of leading role prefix.

    NaN → (None, None). Empty after stripping → (role, None).
    """
    if pd.isna(respondent):
        return None, None
    name = str(respondent).strip()
    if not name:
        return None, None
    low = name.lower()
    role = None
    for prefix in ROLE_PREFIXES:
        if low.startswith(prefix):
            role = prefix
            name = name[len(prefix):].strip()
            break
    name = re.sub(r"\s+", " ", name)
    return role, (name or None)


def fetch_raw_geojson() -> dict | None:
    if RAW_GEOJSON_PATH.exists():
        try:
            return json.loads(RAW_GEOJSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    for url in (GEOJSON_URL, GEOJSON_URL_FALLBACK):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"}
            )
            data = urllib.request.urlopen(req, timeout=45).read()
            RAW_GEOJSON_PATH.write_bytes(data)
            return json.loads(data)
        except Exception as e:
            print(f"  WARN: could not download {url} ({e})")
    return None


def main() -> int:
    print(f"reading {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    print(f"  input rows: {len(df)}")

    # Preserve the original oblast in a separate column; compute the
    # ethnographic region but allow it to be null (for Unknown / Podillia
    # (historical) rows). We keep ALL rows so that a user reaching a
    # singer via recommendations — famous kobzari like Ostap Veresai are
    # tagged region=Unknown in the source CSV — still sees their repertoire.
    df["oblast"] = df["region"].astype("object")

    def to_ethno(r) -> str | None:
        if not isinstance(r, str):
            return None
        if r == PODILLIA_HISTORICAL:
            return "Podillia"
        return OBLAST_TO_ETHNO.get(r)

    df["region"] = df["oblast"].map(to_ethno)
    mapped_n = int(df["region"].notna().sum())
    print(
        f"  {len(df)} songs kept; {mapped_n} mapped to an ethnographic "
        f"region, {len(df) - mapped_n} left as region=null (not drawn on the "
        f"map but still reachable via singer/song links)."
    )

    df["year"] = df["year_recorded"].map(extract_year)

    # Parse a cell holding a list of strings. The recommendations CSV uses
    # Python-repr style (single quotes) which json.loads rejects, so we
    # fall back to ast.literal_eval.
    import ast

    def parse_themes(v) -> list[str]:
        if pd.isna(v):
            return []
        s = str(v).strip()
        if not s:
            return []
        for loader in (json.loads, ast.literal_eval):
            try:
                val = loader(s)
                if isinstance(val, list):
                    return [str(x) for x in val]
            except Exception:
                continue
        return []

    if "themes" in df.columns:
        df["_themes"] = df["themes"].apply(parse_themes)
    else:
        df["_themes"] = [[] for _ in range(len(df))]

    # similar_songs is a JSON-encoded list of song_ids, present only in the
    # recommendations CSV. Fall back to empty list.
    if "similar_songs" in df.columns:
        df["_similar"] = df["similar_songs"].apply(parse_themes)
    else:
        df["_similar"] = [[] for _ in range(len(df))]

    if "primary_theme" in df.columns:
        df["_primary"] = df["primary_theme"].where(df["primary_theme"].notna(), None)
    else:
        df["_primary"] = None

    # Attach valence/arousal. Two paths:
    #   (a) The CSV already has them (preferred — real analysis).
    #   (b) Derive from the song's theme list using THEME_EMOTION_PRIORS
    #       with a deterministic hash-based jitter so identical theme sets
    #       don't stack on a single point.
    import hashlib
    have_va = "valence" in df.columns and "arousal" in df.columns
    if have_va:
        df["_valence"] = df["valence"].astype(float)
        df["_arousal"] = df["arousal"].astype(float)
        print("  using valence/arousal columns from source CSV")
    else:
        print(
            f"  WARN: {_EMO_CSV.name} not found — deriving valence/arousal "
            f"from themes with small jitter."
        )

        def jitter(seed: str) -> tuple[float, float]:
            h = hashlib.md5(seed.encode("utf-8")).digest()
            # two stable floats in [-0.22, +0.22]
            dx = ((h[0] / 255) - 0.5) * 0.44
            dy = ((h[1] / 255) - 0.5) * 0.44
            return dx, dy

        def emotion_for_row(row) -> tuple[float, float]:
            themes = row["_themes"] or []
            hits = [
                (t, THEME_EMOTION_PRIORS[t])
                for t in themes
                if t in THEME_EMOTION_PRIORS
            ]
            if not hits:
                return 0.0, 0.0
            primary = row["_primary"] if isinstance(row["_primary"], str) else None
            # Weight the primary theme at 0.7, average the rest at 0.3.
            # Without this weighting, 3-theme songs wash out to the center.
            if primary and primary in THEME_EMOTION_PRIORS and len(hits) > 1:
                pv, pa = THEME_EMOTION_PRIORS[primary]
                others = [p for t, p in hits if t != primary]
                if others:
                    ov = sum(x[0] for x in others) / len(others)
                    oa = sum(x[1] for x in others) / len(others)
                    v = 0.7 * pv + 0.3 * ov
                    a = 0.7 * pa + 0.3 * oa
                else:
                    v, a = pv, pa
            else:
                v = sum(p[0] for _, p in hits) / len(hits)
                a = sum(p[1] for _, p in hits) / len(hits)
            dv, da = jitter(str(row["song_id"]))
            v = max(-1.0, min(1.0, v + dv))
            a = max(-1.0, min(1.0, a + da))
            return v, a

        out = df.apply(emotion_for_row, axis=1)
        df["_valence"] = [p[0] for p in out]
        df["_arousal"] = [p[1] for p in out]
    df[["_role", "_name"]] = df["respondent"].apply(
        lambda r: pd.Series(split_role(r))
    )

    # singer_id comes from the upstream CSV (oblast-prefixed). If the
    # column is missing (e.g. running against the older themes CSV), fall
    # back to regenerating it from the respondent string + the song's
    # *oblast* (not the ethno region) so the IDs stay consistent with
    # whatever singers.json would contain.
    if "singer_id" not in df.columns:
        def regen(row) -> str:
            oblast = row["oblast"] if isinstance(row["oblast"], str) else "unknown"
            name = row["_name"]
            if not isinstance(name, str) or not name.strip():
                return f"{slugify(oblast)}--"
            return f"{slugify(oblast)}--{slugify(name)}"
        df["singer_id"] = df.apply(regen, axis=1)

    # The per-song singer_name / singer_role are still useful for the song
    # detail view (the raw respondent line, before we look up the canonical
    # singer record in singers.json).
    df["singer_name"] = df["_name"].where(
        df["_name"].apply(lambda x: isinstance(x, str) and x.strip() != ""),
        None,
    )
    df["singer_role"] = df["_role"]

    # songs.json — include oblast (original) alongside region (ethno).
    songs = []
    for _, r in df.iterrows():
        songs.append({
            "song_id": r["song_id"],
            "title": r["title"] if pd.notna(r["title"]) else None,
            "region": r["region"] if isinstance(r["region"], str) else None,
            "oblast": r["oblast"] if isinstance(r["oblast"], str) else None,
            "country": r["country"] if pd.notna(r["country"]) else "Ukraine",
            "genre": r["genre"] if pd.notna(r["genre"]) else None,
            "year": int(r["year"]) if pd.notna(r["year"]) else None,
            "year_raw": r["year_recorded"] if pd.notna(r["year_recorded"]) else None,
            "collector": r["collector"] if pd.notna(r["collector"]) else None,
            "singer_id": r["singer_id"],
            "singer_name": r["singer_name"] if pd.notna(r["singer_name"]) else None,
            "singer_role": r["singer_role"] if pd.notna(r["singer_role"]) else None,
            "line_count": int(r["line_count"]) if pd.notna(r["line_count"]) else 0,
            "word_count": int(r["word_count"]) if pd.notna(r["word_count"]) else 0,
            "full_text": r["full_text"] if pd.notna(r["full_text"]) else "",
            "place_raw": r["place_raw"] if pd.notna(r["place_raw"]) else None,
            "themes": list(r["_themes"]) if isinstance(r["_themes"], list) else [],
            "primary_theme": (
                r["_primary"] if isinstance(r["_primary"], str) and r["_primary"] else None
            ),
            "valence": round(float(r["_valence"]), 4),
            "arousal": round(float(r["_arousal"]), 4),
            "similar_songs": (
                list(r["_similar"]) if isinstance(r["_similar"], list) else []
            ),
        })

    # singers.json — passthrough from project root. No aggregation here;
    # the upstream file already contains name/role/song_ids/similar_singers.
    # We only sanitize each singer to the songs actually present in the
    # final songs.json (in case the singers file references a superset).
    present_ids = {s["song_id"] for s in songs}
    singers: list[dict] = []
    if SINGERS_SRC.exists():
        raw = json.loads(SINGERS_SRC.read_text(encoding="utf-8"))
        for s in raw:
            keep_songs = [sid for sid in s.get("song_ids", []) if sid in present_ids]
            if not keep_songs:
                continue
            singers.append({
                "singer_id": s["singer_id"],
                "name": s.get("name") or None,
                "role": s.get("role") or None,
                "region": s.get("region"),
                "country": s.get("country", "Ukraine"),
                "song_count": len(keep_songs),
                "song_ids": keep_songs,
                "similar_singers": list(s.get("similar_singers", [])),
            })
    else:
        print(f"  WARN: {SINGERS_SRC.name} not found — deriving singers from CSV")
        for sid, sub in df.groupby("singer_id"):
            first = sub.iloc[0]
            role_vals = sub["singer_role"].dropna()
            role = role_vals.mode().iloc[0] if not role_vals.empty else None
            name = first["singer_name"] if pd.notna(first["singer_name"]) else None
            singers.append({
                "singer_id": sid,
                "name": name,
                "role": role,
                "region": first["oblast"] if isinstance(first["oblast"], str) else None,
                "country": first["country"] if pd.notna(first["country"]) else "Ukraine",
                "song_count": int(len(sub)),
                "song_ids": sub["song_id"].tolist(),
                "similar_singers": [],
            })

    # --- Build geometry.
    #
    # Step 1: pull the 16 oblast polygons (robust Ukrainian-stem match).
    # Step 2: write them to ukraine_oblasts.geojson (archival — not used by
    #         the UI, but kept in case we need to revert or show both views).
    # Step 3: dissolve the oblasts into ethnographic regions via
    #         unary_union, derive label positions, and write them to
    #         ukraine_ethno_regions.geojson — this is what the UI loads.
    raw_gj = fetch_raw_geojson()
    oblast_geoms: dict[str, "object"] = {}  # oblast English name -> shapely geom
    oblast_features: list[dict] = []
    data_ethnos = {r for r in df["region"].unique() if isinstance(r, str)}
    mapped_count = 0
    unmapped: list[str] = []
    gj_out = None
    # ethno region -> (label_lng, label_lat, minx, miny, maxx, maxy)
    region_geom_info: dict[str, tuple[float, float, float, float, float, float]] = {}

    if raw_gj is not None:
        seen_oblasts: set[str] = set()
        for feat in raw_gj.get("features", []):
            props = feat.get("properties") or {}
            shape_name = props.get("shapeName", "")
            oblast = SHAPENAME_TO_OBLAST.get(shape_name)
            if oblast is None or oblast not in OBLAST_TO_ETHNO:
                continue
            if oblast in seen_oblasts:
                print(f"  WARN: duplicate match for {oblast} "
                      f"(shapeName={shape_name!r}); keeping first")
                continue
            seen_oblasts.add(oblast)
            geom = make_valid(shape(feat["geometry"]))
            oblast_geoms[oblast] = geom
            oblast_features.append({
                "type": "Feature",
                "properties": {
                    "region": oblast,
                    "shapeName": shape_name,
                    "shapeISO": props.get("shapeISO"),
                },
                "geometry": mapping(geom),
            })

        expected_oblasts = set(OBLAST_TO_ETHNO.keys())
        missing_oblasts = expected_oblasts - seen_oblasts
        if missing_oblasts:
            print(f"  WARN: oblasts not found in source geojson: "
                  f"{sorted(missing_oblasts)}")

        # Dissolve oblasts into ethnographic regions.
        eth_features: list[dict] = []
        for ethno in sorted(set(OBLAST_TO_ETHNO.values())):
            geoms = [
                g for ob, g in oblast_geoms.items()
                if OBLAST_TO_ETHNO[ob] == ethno
            ]
            if not geoms:
                unmapped.append(ethno)
                continue
            # Tiny dilate → union → erode closes micro-gaps between oblast
            # borders if they aren't perfectly coincident (≈50 m at these
            # latitudes). With the edge-matched geoBoundaries source this is
            # usually unnecessary, but it's cheap insurance against seams.
            dilated = [g.buffer(0.0005) for g in geoms]
            merged = unary_union(dilated).buffer(-0.0005)
            merged = make_valid(merged)
            # Drop tiny slivers left by the dilate/erode + hole artifacts
            # (e.g. the Kyiv-city donut leaves a ~0.0003 deg² scrap inside
            # Naddniprianshchyna). Keep anything ≥1% of the largest piece
            # when the geom is a MultiPolygon.
            if merged.geom_type == "MultiPolygon":
                pieces = list(merged.geoms)
                largest_area = max(p.area for p in pieces)
                kept = [p for p in pieces if p.area >= largest_area * 0.01]
                if len(kept) != len(pieces):
                    print(f"  INFO: {ethno} — dropped "
                          f"{len(pieces) - len(kept)} sliver(s)")
                if len(kept) == 1:
                    merged = kept[0]
                else:
                    from shapely.geometry import MultiPolygon
                    merged = MultiPolygon(kept)

            # Label position: for MultiPolygons (Pivden: mainland + Crimea;
            # Polissia: Zhytomyr-Rivne block + Chernihiv), the
            # representative_point of the whole MultiPolygon can land on a
            # small piece. Use the largest sub-polygon's interior point so
            # the label ends up on the visually dominant landmass.
            if merged.geom_type == "MultiPolygon":
                largest = max(merged.geoms, key=lambda g: g.area)
                pt = largest.representative_point()
            else:
                c = merged.centroid
                pt = c if merged.contains(c) else merged.representative_point()
            minx, miny, maxx, maxy = merged.bounds
            region_geom_info[ethno] = (pt.x, pt.y, minx, miny, maxx, maxy)
            eth_features.append({
                "type": "Feature",
                "properties": {
                    "region": ethno,
                    "label_lng": pt.x,
                    "label_lat": pt.y,
                    "geom_type": merged.geom_type,
                },
                "geometry": mapping(merged),
            })
            mapped_count += 1

        for ethno in sorted(data_ethnos):
            if ethno not in region_geom_info:
                unmapped.append(ethno)

        gj_out = {"type": "FeatureCollection", "features": eth_features}
    else:
        unmapped = sorted(data_ethnos)

    # --- regions.json — centroid is now the polygon's point-on-surface.
    # Count only NAMED singers per ethno region (unknown buckets don't
    # count toward "singers in this region").
    named_singers_by_ethno: dict[str, set[str]] = {}
    for s in singers:
        if not s["name"]:
            continue
        ob = s["region"]
        ethno = "Podillia" if ob == PODILLIA_HISTORICAL else OBLAST_TO_ETHNO.get(ob)
        if not ethno:
            continue
        named_singers_by_ethno.setdefault(ethno, set()).add(s["singer_id"])

    regions = []
    for region, sub in df.groupby("region"):
        country = sub["country"].dropna().iloc[0] if not sub["country"].dropna().empty else "Ukraine"
        info = region_geom_info.get(region)
        if info is None:
            continue
        lng, lat, minx, miny, maxx, maxy = info
        regions.append({
            "region": region,
            "country": country,
            "song_count": int(len(sub)),
            "singer_count": len(named_singers_by_ethno.get(region, set())),
            "centroid": [lng, lat],
            "bbox": [[minx, miny], [maxx, maxy]],
        })
    regions.sort(key=lambda r: -r["song_count"])

    # write outputs
    def dump(obj):
        return json.dumps(obj, ensure_ascii=False, allow_nan=False)

    (OUT_DIR / "songs.json").write_text(dump(songs), encoding="utf-8")
    (OUT_DIR / "singers.json").write_text(dump(singers), encoding="utf-8")
    (OUT_DIR / "regions.json").write_text(dump(regions), encoding="utf-8")

    # Copy the curated themes.json through to the public data dir. The
    # counts in themes.json are authoritative (manually curated order,
    # label casing); we validate they match what's in the CSV but don't
    # overwrite them.
    if THEMES_SRC.exists():
        themes = json.loads(THEMES_SRC.read_text(encoding="utf-8"))
        (OUT_DIR / "themes.json").write_text(dump(themes), encoding="utf-8")
        from collections import Counter
        any_c: Counter[str] = Counter()
        for tl in df["_themes"]:
            for t in tl:
                any_c[t] += 1
        mismatched = []
        for t in themes:
            csv_count = any_c.get(t["id"], 0)
            if csv_count != t["song_count"]:
                mismatched.append((t["id"], t["song_count"], csv_count))
        if mismatched:
            print("  WARN: themes.json counts disagree with CSV:")
            for tid, declared, actual in mismatched:
                print(f"    {tid}: themes.json={declared} csv={actual}")
    else:
        print(f"  WARN: {THEMES_SRC} not found — skipping themes.json emit")
    # Archival oblast geojson — kept in case we ever revert or show both views.
    if oblast_features:
        (OUT_DIR / "ukraine_oblasts.geojson").write_text(
            dump({"type": "FeatureCollection", "features": oblast_features}),
            encoding="utf-8",
        )
    # This is what the UI loads.
    if gj_out is not None:
        (OUT_DIR / "ukraine_ethno_regions.geojson").write_text(
            dump(gj_out), encoding="utf-8"
        )

    print()
    print("=" * 72)
    print("SUMMARY")
    print("=" * 72)
    print(f"  songs.json      rows = {len(songs)}")
    print(f"  singers.json    rows = {len(singers)}")
    print(f"  regions.json    rows = {len(regions)}")
    print(f"  oblasts pulled from source      = {len(oblast_geoms)}")
    print(f"  ethnographic regions dissolved  = {mapped_count}")
    if gj_out is None:
        print("  WARN: geojson download failed — UI will fall back to "
              "circle markers at centroids.")
    if unmapped:
        print(f"  WARN: regions with no geojson feature = {unmapped}")
    else:
        print("  all data regions have matching geojson features")

    print()
    print("  region -> polygon label (point-on-surface):")
    for r in sorted(regions, key=lambda r: -r["song_count"]):
        print(f"    {r['region']:<22} "
              f"[{r['centroid'][0]:6.2f}, {r['centroid'][1]:6.2f}]  "
              f"songs={r['song_count']:<5} singers={r['singer_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
