"""Exploration script for songs_merged.csv — run this before building UI."""
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "songs_merged.csv"

df = pd.read_csv(CSV)

print("=" * 70)
print("1. SHAPE / COLUMNS / DTYPES")
print("=" * 70)
print(f"rows: {len(df)}")
print(f"columns: {list(df.columns)}")
print("dtypes:")
print(df.dtypes.to_string())

print()
print("=" * 70)
print("2. REGION VALUE COUNTS")
print("=" * 70)
print(df["region"].value_counts(dropna=False).to_string())

print()
print("=" * 70)
print("3. UNIQUE RESPONDENTS PER REGION (raw, before normalization)")
print("=" * 70)
for region, sub in df.groupby("region", dropna=False):
    n_nan = sub["respondent"].isna().sum()
    n_uniq = sub["respondent"].dropna().nunique()
    print(f"  {str(region):<28} rows={len(sub):<5} unique_respondents={n_uniq:<5} nan={n_nan}")

print()
print("=" * 70)
print("4. SAMPLE RESPONDENT STRINGS (look for role prefixes & whitespace)")
print("=" * 70)
samples = df["respondent"].dropna().drop_duplicates().head(40)
for s in samples:
    print(f"  [{s!r}]")

print()
print("   respondents containing 'кобзар':")
mask = df["respondent"].fillna("").str.lower().str.contains("кобзар")
print(df.loc[mask, "respondent"].drop_duplicates().head(15).to_string(index=False))

print()
print("   respondents containing 'лірник':")
mask = df["respondent"].fillna("").str.lower().str.contains("лірник")
print(df.loc[mask, "respondent"].drop_duplicates().head(15).to_string(index=False))

print()
print("   respondents containing 'бандурист':")
mask = df["respondent"].fillna("").str.lower().str.contains("бандурист")
print(df.loc[mask, "respondent"].drop_duplicates().head(15).to_string(index=False))

print()
print("=" * 70)
print("5. SAMPLE year_recorded STRINGS + regex extraction")
print("=" * 70)
year_re = re.compile(r"(1[6-9]\d{2}|20[0-2]\d)")

year_samples = df["year_recorded"].dropna().drop_duplicates().head(30)
for s in year_samples:
    m = year_re.search(str(s))
    print(f"  raw={str(s)!r:<40} -> {m.group(1) if m else None}")

extracted = df["year_recorded"].fillna("").astype(str).map(
    lambda s: int(year_re.search(s).group(1)) if year_re.search(s) else None
)
print()
print(f"  rows with year_recorded present: {df['year_recorded'].notna().sum()}")
print(f"  rows where regex matched a year: {extracted.notna().sum()}")
print(f"  year range: {extracted.min()} – {extracted.max()}")
