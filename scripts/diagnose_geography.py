"""Geography diagnostic — runs A/B/C from the bug-fix prompt.

Prints what we have now before changing anything, so the bug location
is provable, not guessed.
"""
from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "public" / "data" / "ukraine_raw.geojson"
FILTERED = ROOT / "public" / "data" / "ukraine_oblasts.geojson"
REGIONS_JSON = ROOT / "public" / "data" / "regions.json"


def print_header(s: str) -> None:
    print()
    print("=" * 72)
    print(s)
    print("=" * 72)


# -----------------------------------------------------------------------------
# A. raw geojson
# -----------------------------------------------------------------------------
print_header("A. RAW GEOJSON  (public/data/ukraine_raw.geojson)")
raw = json.loads(RAW.read_text(encoding="utf-8"))
print(f"feature count: {len(raw['features'])}")
for i, f in enumerate(raw["features"]):
    p = f["properties"]
    # only string-valued properties, and skip the enormous `name:xx` block
    strs = {
        k: v
        for k, v in p.items()
        if isinstance(v, str) and (not k.startswith("name:") or k in ("name:en", "name:uk", "name:ru"))
    }
    geom = shape(f["geometry"])
    try:
        pt = geom.representative_point()
        cent = geom.centroid
    except Exception as e:
        pt = None
        cent = None
        print(f"  [{i:02d}] GEOM ERROR: {e}")
    print(
        f"  [{i:02d}] "
        f"name={strs.get('name')!r} "
        f"name:uk={strs.get('name:uk')!r} "
        f"name:en={strs.get('name:en')!r} "
        f"iso={strs.get('iso3166-2')!r}"
    )
    if pt is not None:
        print(
            f"        centroid=[{cent.x:.3f}, {cent.y:.3f}]  "
            f"rep_point=[{pt.x:.3f}, {pt.y:.3f}]"
        )

# -----------------------------------------------------------------------------
# B. filtered geojson + regions.json centroid comparison
# -----------------------------------------------------------------------------
print_header("B. FILTERED GEOJSON vs regions.json centroids")
filt = json.loads(FILTERED.read_text(encoding="utf-8"))
regions = json.loads(REGIONS_JSON.read_text(encoding="utf-8"))
region_centroids = {r["region"]: tuple(r["centroid"]) for r in regions}

print(f"filtered feature count: {len(filt['features'])}")
print()
print(
    f"  {'region':<18} {'poly centroid':<22} {'regions.json centroid':<22} {'delta (deg)'}"
)
print("  " + "-" * 78)
for f in filt["features"]:
    region = f["properties"]["region"]
    geom = shape(f["geometry"])
    c = geom.centroid
    rc = region_centroids.get(region)
    if rc is None:
        print(f"  {region:<18} NOT in regions.json")
        continue
    delta = ((c.x - rc[0]) ** 2 + (c.y - rc[1]) ** 2) ** 0.5
    flag = " <-- OFF" if delta > 0.5 else ""
    print(
        f"  {region:<18} [{c.x:6.2f}, {c.y:6.2f}]   "
        f"[{rc[0]:6.2f}, {rc[1]:6.2f}]   {delta:5.2f}{flag}"
    )

# -----------------------------------------------------------------------------
# C. lookup table used by prepare_data.py
# -----------------------------------------------------------------------------
print_header("C. REGION → GEOJSON NAME LOOKUP (as used by prepare_data.py)")
import importlib.util, sys as _sys
spec = importlib.util.spec_from_file_location(
    "prepare_data", ROOT / "scripts" / "prepare_data.py"
)
mod = importlib.util.module_from_spec(spec)
# Don't run the script (it has side effects) — just import the module object.
# The constants are at module top level before main(), so exec_module will run
# the whole file. We guard with SKIP_MAIN env.
import os
os.environ["SKIP_MAIN"] = "1"
# Actually easier: re-parse the constant out of the file textually.
text = (ROOT / "scripts" / "prepare_data.py").read_text(encoding="utf-8")
marker = "REGION_UK_STEMS: dict[str, list[str]] = {"
if marker in text:
    start = text.index(marker)
    # match the matching close brace
    depth = 0
    end = start
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    print(text[start:end])
else:
    print("  (could not locate mapping constant)")

# -----------------------------------------------------------------------------
# D. Spot-check the 4 reference oblasts
# -----------------------------------------------------------------------------
print_header("D. SPOT CHECK against Wikipedia reference coordinates")
expected = {
    "Vinnytska":  (28.5, 49.2),
    "Poltava":    (34.6, 49.6),
    "Chernihiv":  (31.9, 51.4),
    "Sumy":       (34.8, 50.9),
    "Kharkiv":    (36.3, 49.8),
    "Lviv":       (24.0, 49.6),
    "Crimea":     (34.1, 45.4),
}
# Look up each in the filtered geojson and compute real polygon centroid
by_region = {f["properties"]["region"]: f for f in filt["features"]}
for region, exp in expected.items():
    f = by_region.get(region)
    if f is None:
        print(f"  {region}: MISSING from filtered geojson")
        continue
    c = shape(f["geometry"]).centroid
    delta = ((c.x - exp[0]) ** 2 + (c.y - exp[1]) ** 2) ** 0.5
    flag = " <-- WRONG POLYGON" if delta > 1.0 else ""
    print(
        f"  {region:<14} poly=[{c.x:6.2f}, {c.y:6.2f}]  "
        f"expected=[{exp[0]:6.2f}, {exp[1]:6.2f}]  delta={delta:5.2f}{flag}"
    )
