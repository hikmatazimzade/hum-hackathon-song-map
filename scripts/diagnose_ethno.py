"""Diagnose the ethnographic-region dissolve.

Reads the currently-written /public/data/ukraine_oblasts.geojson and the
OBLAST_TO_ETHNO constant from scripts/prepare_data.py. Reports:
  a) which of the 16 expected oblasts are present/absent in the source file
  b) the oblast -> ethno mapping
  c) for each ethno region: which oblasts were merged, bbox, rep_point
  d) whether each merged geom is valid and how many pieces it has
  e) comparison of actual vs expected bboxes
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
OBLAST_GJ = ROOT / "public" / "data" / "ukraine_oblasts.geojson"
ETHNO_GJ = ROOT / "public" / "data" / "ukraine_ethno_regions.geojson"

EXPECTED_OBLASTS = {
    "Vinnytska", "Volyn", "Dnipropetrovsk", "Zhytomyr", "Ivano-Frankivsk",
    "Kyiv", "Lviv", "Mykolaiv", "Poltava", "Sumy", "Kharkiv", "Kherson",
    "Khmelnytskyi", "Cherkasy", "Chernihiv", "Crimea",
}

EXPECTED_BBOX = {
    "Polissia":           (27.0, 50.3, 33.5, 52.4),
    "Volyn":              (23.8, 50.1, 26.0, 51.9),
    "Podillia":           (26.2, 47.8, 30.3, 50.4),
    "Naddniprianshchyna": (29.5, 47.8, 36.3, 51.6),
    "Slobozhanshchyna":   (33.2, 48.3, 40.2, 51.9),
    "Pivden":             (31.1, 44.3, 36.6, 48.3),
    "Halychyna":          (22.1, 48.2, 25.5, 50.9),
}


def extract_dict(path: Path, var: str) -> dict[str, str]:
    """Pull a `VAR: dict[str, str] = { ... }` literal out of a .py file."""
    text = path.read_text(encoding="utf-8")
    m = re.search(rf"{var}\s*:\s*dict\[str,\s*str\]\s*=\s*\{{", text)
    assert m, f"could not find {var} in {path}"
    start = m.end() - 1
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                body = text[start + 1 : i]
                break
    out: dict[str, str] = {}
    for line in body.splitlines():
        mm = re.match(r'\s*"([^"]+)"\s*:\s*"([^"]+)"\s*,?', line)
        if mm:
            out[mm.group(1)] = mm.group(2)
    return out


# ---------------------------------------------------------------------------
# a) Oblasts in oblast geojson
# ---------------------------------------------------------------------------
print("=" * 74)
print("a) OBLASTS IN public/data/ukraine_oblasts.geojson")
print("=" * 74)
ob_gj = json.loads(OBLAST_GJ.read_text(encoding="utf-8"))
print(f"feature count: {len(ob_gj['features'])}")
found = set()
ob_geoms: dict[str, object] = {}
for f in ob_gj["features"]:
    region = f["properties"].get("region")
    geom = shape(f["geometry"])
    c = geom.centroid
    minx, miny, maxx, maxy = geom.bounds
    print(
        f"  {region!r:<22} centroid=[{c.x:6.2f}, {c.y:6.2f}]  "
        f"bbox=[{minx:6.2f}, {miny:6.2f}, {maxx:6.2f}, {maxy:6.2f}]  "
        f"valid={geom.is_valid}  type={f['geometry']['type']}"
    )
    found.add(region)
    ob_geoms[region] = geom

missing = EXPECTED_OBLASTS - found
extra = found - EXPECTED_OBLASTS
print(f"\n  expected {len(EXPECTED_OBLASTS)} oblasts; found {len(found)}")
print(f"  MISSING : {sorted(missing) or 'none'}")
print(f"  EXTRA   : {sorted(extra) or 'none'}")

# ---------------------------------------------------------------------------
# b) OBLAST_TO_ETHNO mapping
# ---------------------------------------------------------------------------
print()
print("=" * 74)
print("b) OBLAST_TO_ETHNO (from scripts/prepare_data.py)")
print("=" * 74)
mapping = extract_dict(ROOT / "scripts" / "prepare_data.py", "OBLAST_TO_ETHNO")
for ob, eth in mapping.items():
    in_gj = "yes" if ob in found else "NO <-- not in geojson!"
    print(f"  {ob:<20} -> {eth:<22} (in oblast geojson: {in_gj})")

# ---------------------------------------------------------------------------
# c) Re-run the dissolve here and inspect
# ---------------------------------------------------------------------------
print()
print("=" * 74)
print("c) DISSOLVE RESULT (recomputed here, independent of pipeline output)")
print("=" * 74)
by_ethno: dict[str, list[str]] = {}
for ob, eth in mapping.items():
    by_ethno.setdefault(eth, []).append(ob)

for eth, oblasts in sorted(by_ethno.items()):
    present = [o for o in oblasts if o in ob_geoms]
    missing_here = [o for o in oblasts if o not in ob_geoms]
    print(f"\n  {eth}  (expected oblasts: {oblasts})")
    print(f"    present in geojson: {present}")
    if missing_here:
        print(f"    MISSING           : {missing_here}")
    if not present:
        continue

    # Dissolve two ways, so we can tell if buffer(0) is dropping pieces.
    raw_geoms = [ob_geoms[o] for o in present]
    validities = [(o, g.is_valid) for o, g in zip(present, raw_geoms)]
    print(f"    per-oblast is_valid: {validities}")

    try:
        merged_raw = unary_union(raw_geoms)
        raw_ok = True
    except Exception as e:
        print(f"    unary_union(raw)   CRASHED: {e}")
        merged_raw = None
        raw_ok = False

    buffered = [g.buffer(0) for g in raw_geoms]
    merged_buf = unary_union(buffered)

    if raw_ok and merged_raw is not None:
        n_raw = (
            len(list(merged_raw.geoms)) if merged_raw.geom_type == "MultiPolygon" else 1
        )
        print(f"    merged_raw type={merged_raw.geom_type} pieces={n_raw}  "
              f"bbox={tuple(round(v, 2) for v in merged_raw.bounds)}")

    n_buf = (
        len(list(merged_buf.geoms)) if merged_buf.geom_type == "MultiPolygon" else 1
    )
    print(
        f"    merged_buf type={merged_buf.geom_type} pieces={n_buf}  "
        f"bbox={tuple(round(v, 2) for v in merged_buf.bounds)}"
    )

    exp = EXPECTED_BBOX.get(eth)
    if exp:
        aminx, aminy, amaxx, amaxy = merged_buf.bounds
        eminx, eminy, emaxx, emaxy = exp
        # flag if actual bbox is significantly smaller than expected
        width_ratio = (amaxx - aminx) / max(1e-9, emaxx - eminx)
        height_ratio = (amaxy - aminy) / max(1e-9, emaxy - eminy)
        print(
            f"    expected bbox approx: {exp}"
        )
        if width_ratio < 0.6 or height_ratio < 0.6:
            print(
                f"    <-- SMALL  "
                f"width_ratio={width_ratio:.2f} height_ratio={height_ratio:.2f}"
            )

# ---------------------------------------------------------------------------
# d) What's actually in ukraine_ethno_regions.geojson (what the UI loads)
# ---------------------------------------------------------------------------
print()
print("=" * 74)
print("d) FEATURES ACTUALLY WRITTEN TO ukraine_ethno_regions.geojson")
print("=" * 74)
if ETHNO_GJ.exists():
    eth_gj = json.loads(ETHNO_GJ.read_text(encoding="utf-8"))
    for f in eth_gj["features"]:
        p = f["properties"]
        g = shape(f["geometry"])
        pieces = len(list(g.geoms)) if g.geom_type == "MultiPolygon" else 1
        print(
            f"  {p['region']:<22} type={f['geometry']['type']:<13} pieces={pieces}  "
            f"bbox={tuple(round(v, 2) for v in g.bounds)}  "
            f"label=[{p.get('label_lng'):.2f}, {p.get('label_lat'):.2f}]"
        )
else:
    print(f"  file not found: {ETHNO_GJ}")
