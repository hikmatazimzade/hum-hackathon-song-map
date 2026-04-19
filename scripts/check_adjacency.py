"""Verify the dissolved ethnographic-region polygons touch where the
reference map says they should. Run after prepare_data.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parent.parent
ETHNO = ROOT / "public" / "data" / "ukraine_ethno_regions.geojson"

ADJACENCY_REQUIREMENTS: list[tuple[str, str]] = [
    ("Polissia", "Volyn"),
    ("Polissia", "Halychyna"),
    ("Polissia", "Podillia"),
    ("Polissia", "Naddniprianshchyna"),
    ("Polissia", "Slobozhanshchyna"),
    ("Volyn", "Halychyna"),
    ("Volyn", "Podillia"),
    ("Halychyna", "Podillia"),
    ("Podillia", "Naddniprianshchyna"),
    ("Podillia", "Pivden"),
    ("Naddniprianshchyna", "Slobozhanshchyna"),
    ("Naddniprianshchyna", "Pivden"),
    ("Slobozhanshchyna", "Pivden"),
]

EXPECTED_BBOX = {
    "Polissia":           (24.0, 50.3, 33.5, 52.4),
    "Volyn":              (23.8, 50.1, 26.0, 51.9),
    "Halychyna":          (22.1, 48.2, 26.2, 50.9),
    "Podillia":           (26.2, 47.8, 30.3, 50.4),
    "Naddniprianshchyna": (29.5, 47.5, 36.3, 51.6),
    "Slobozhanshchyna":   (33.2, 48.3, 40.2, 51.9),
    "Pivden":             (31.1, 44.3, 36.6, 48.3),
}

fc = json.loads(ETHNO.read_text(encoding="utf-8"))
regions = {f["properties"]["region"]: shape(f["geometry"]) for f in fc["features"]}

# --- Adjacency -----------------------------------------------------------
print("Adjacency check:")
failures: list[tuple[str, str, float]] = []
for a, b in ADJACENCY_REQUIREMENTS:
    if a not in regions or b not in regions:
        print(f"  {a} <-> {b}: SKIP (one side missing)")
        continue
    ga, gb = regions[a], regions[b]
    # intersects with a tiny buffer is tolerant of floating-point seams
    touches = ga.buffer(0.001).intersects(gb)
    if touches:
        print(f"  {a:<20} <-> {b:<20} OK")
    else:
        gap = ga.distance(gb)
        print(f"  {a:<20} <-> {b:<20} FAIL  gap={gap:.4f}° ({gap*111:.1f} km)")
        failures.append((a, b, gap))

print()
print("Bounding-box check:")
bbox_bad = 0
for region, (eminx, eminy, emaxx, emaxy) in EXPECTED_BBOX.items():
    if region not in regions:
        print(f"  {region}: MISSING")
        continue
    g = regions[region]
    aminx, aminy, amaxx, amaxy = g.bounds
    # per-side tolerance 1° per the brief
    deltas = [
        abs(aminx - eminx),
        abs(aminy - eminy),
        abs(amaxx - emaxx),
        abs(amaxy - emaxy),
    ]
    worst = max(deltas)
    flag = " <-- OFF" if worst > 1.0 else ""
    print(
        f"  {region:<20} actual=[{aminx:6.2f},{aminy:6.2f},{amaxx:6.2f},{amaxy:6.2f}] "
        f"expected=[{eminx:6.2f},{eminy:6.2f},{emaxx:6.2f},{emaxy:6.2f}] "
        f"worstΔ={worst:.2f}{flag}"
    )
    if worst > 1.0:
        bbox_bad += 1

print()
if failures:
    print(f"!! ADJACENCY FAILURES: {len(failures)}")
    for a, b, d in failures:
        print(f"   {a} <-> {b}: gap {d:.4f}° (~{d*111:.1f} km)")
    sys.exit(1)
if bbox_bad:
    print(f"!! BBOX MISMATCHES: {bbox_bad}")
    sys.exit(1)

print("All adjacency + bbox checks passed.")
