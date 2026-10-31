#!/usr/bin/env python3
"""
Check the data/ folder against what the page's charts need. Run from the site folder:
    python check_data.py            (looks in ./data)
Prints OK / PROBLEM lines with the fix. Needs only pandas.
"""
import json
import sys
from pathlib import Path

import pandas as pd

D = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
bad = []


def problem(msg):
    bad.append(msg)
    print("PROBLEM:", msg)


def ok(msg):
    print("OK     :", msg)


NEED = {
    "places_by_era.csv": ["place", "lat", "lon", "kind", "era", "n"],
    "places_all.csv": ["place", "lat", "lon", "kind", "n"],
    "places_top.csv": ["place", "kind", "n"],
    "photos_by_decade.csv": ["decade", "kind", "n"],
    "decade_theme.csv": ["decade", "kind", "theme", "n", "decade_photos"],
    "year_place.csv": ["place", "bin5", "n"],
    "words_by_era.csv": ["era", "word", "n"],
    "waffle_attribution.csv": ["cell", "col", "row", "attribution"],
    "lga_share.csv": ["lga_code", "lga_name", "erp_2025", "photos", "photo_share_pct", "pop_share_pct", "diff_pp"],
}
total = 0
for name, cols in NEED.items():
    p = D / name
    if not p.exists():
        problem(f"{name} is missing from {D}/ (rerun prep_picture_qld.py and copy it in)")
        continue
    total += p.stat().st_size
    df = pd.read_csv(p, dtype={"lga_code": str})
    miss = [c for c in cols if c not in df.columns]
    if miss:
        problem(f"{name} lacks columns {miss}; rerun prep_picture_qld.py / make_lga_share.py from the latest versions")
    elif df.empty:
        problem(f"{name} has no rows")
    else:
        ok(f"{name}: {len(df)} rows")

# the bug seen once: every council area had 0 photos
p = D / "lga_share.csv"
if p.exists():
    s = pd.read_csv(p, dtype={"lga_code": str})
    if "photos" in s and s["photos"].sum() == 0:
        problem("lga_share.csv has 0 photos in every council area: rerun make_lga_share.py with the current data/lga_all.csv")
    elif "diff_pp" in s and s["diff_pp"].isna().any():
        problem("lga_share.csv has blank diff_pp values: rerun make_lga_share.py")
    else:
        ok(f"lga_share.csv: {int(s['photos'].sum())} photos across {int((s['photos'] > 0).sum())} council areas")

# boundary file (build it with: python fix_boundaries.py data/qld_lga.topojson)
p = D / "qld_lga.geojson"
if not p.exists():
    problem("data/qld_lga.geojson is missing. Run: python fix_boundaries.py data/qld_lga.topojson  (or your .geojson). All three maps need this file.")
else:
    total += p.stat().st_size
    g = json.loads(p.read_text())
    feats = g.get("features", []) if g.get("type") == "FeatureCollection" else []
    if not feats:
        problem("qld_lga.geojson is not a FeatureCollection with features. Re-run fix_boundaries.py")
    else:
        codes = {str(f.get("properties", {}).get("lga_code")) for f in feats}
        ok(f"qld_lga.geojson: {len(feats)} council areas")
        if (D / "lga_share.csv").exists():
            sc = set(pd.read_csv(D / "lga_share.csv", dtype=str)["lga_code"])
            hit = len(codes & sc)
            (ok if hit >= 70 else problem)(f"{hit} of {len(sc)} council areas in lga_share.csv match a shape")

print(f"\ntotal size of checked data: {total/1e6:.2f} MB")
print("ALL GOOD" if not bad else f"{len(bad)} problem(s) to fix above")
