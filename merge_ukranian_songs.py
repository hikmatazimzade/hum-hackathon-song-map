"""
Merge all Ukrainian song CSVs into a single unified dataset.

Input:  a folder of metadata + text CSV pairs
Output: one CSV, one row per unique song, with English column names and a
        derived `region` (oblast-level) column.

Usage:
    python merge_ukrainian_songs.py --input ./ukrainian-songs --output songs_merged.csv
"""

import argparse
import os
import re
import sys
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# File registry: (metadata_file, text_file, csv_separator)
# Either side may be None if the pair is incomplete.
# ---------------------------------------------------------------------------
FILE_PAIRS = [
    # (metadata, text, separator)
    ("Dmytrenko_Yefremova_2014_Khmelnytsky_region__-_metadata.csv", None, ","),
    ("Dumy_Vol_1_Hrushevska_metadata.csv",   "Dumy_Vol_1_Hrushevska_texts.csv",   ";"),
    ("Dumy_Vol_1_Skrypnyk_metadata.csv",     "Dumy_Vol_1_Skrypnyk_texts.csv",     ";"),
    ("Dumy_Vol_2_Hrushevska_metadata.csv",   "Dumy_Vol_2_Hrushevska_texts.csv",   ";"),
    ("Dumy_Vol_2_Skrypnyk_metadata.csv",     "Dumy_Vol_2_Skrypnyk_texts.csv",     ";"),
    ("Hrytsa_S__Ukrainski_narodni_dumy-metadata.csv",
     "Hrytsa_S__Ukrainski_narodni_dumy-texts.csv", ","),
    ("Kolessa_Melodii-metadata.csv",         "Kolessa_Melodii-texts.csv",         ","),
    (None, "Kozatski_narodni_dumy_Dumy_nevolnytski-texts.csv", ","),  # orphan texts
    ("Novyi_zbirnyk_narodnykh_pisen_dum_dumok_kolomyiok_i_pisen_vesilnykh-metadata.csv",
     "Novyi_zbirnyk_narodnykh_pisen_dum_dumok_kolomyiok_i_pisen_vesilnykh-texts.csv", ","),
    ("Pisni_Zuikhy_1965_-_metadata.csv",     "Pisni_Zuikhy_1965_-_texts.csv",     ","),
    ("Podillia_songs_-_metadata.csv",        "Podillia_songs_-_texts.csv",        ","),
]

# ---------------------------------------------------------------------------
# Column renames: original (Ukrainian) -> English
# ---------------------------------------------------------------------------
META_RENAME = {
    "song_id":                          "song_id",
    "title":                            "title",
    "genre":                            "genre",
    "Рік запису":                       "year_recorded",
    "Хто записав":                      "collector",
    "Місце запису":                     "place_raw",
    "Респондент":                       "respondent",
    "Вік респондента/рік народження":   "respondent_age_or_birth_year",
}

# ---------------------------------------------------------------------------
# Region extraction. Maps keywords found in `place_raw` -> modern oblast.
# Keywords are substring-matched case-insensitively. Order matters: first hit wins.
# ---------------------------------------------------------------------------
REGION_RULES = [
    ("Vinnytska", ["vinnytska oblast", "вінниц", "vinnyts", "pohrebyshche",
                   "ziatkivtsi", "погребище", "зятківц"]),
    ("Poltava",   ["полтав", "poltav", "миргород", "mirhorod", "лохвиц",
                   "сорочинц", "гадяч", "прилук", "зіньків", "пирятин",
                   "лубен", "кобеляц", "кременчу", "ромен", "хорол", "глинськ"]),
    ("Kharkiv",   ["харків", "kharkiv", "богодух", "ізюм", "охтирк", "валк",
                   "куп'янськ", "красноград", "костянтиноград"]),
    ("Chernihiv", ["чернігів", "chernihiv", "сосниц", "ніжин", "борзен",
                   "березн", "ічня", "талалаїв", "корюків", "новгород-сіверськ"]),
    ("Sumy",      ["сум", "sumy", "роменськ", "глухів", "конотоп"]),
    ("Kyiv",      ["київ", "kyiv", "київщ"]),
    ("Khmelnytskyi", ["хмельниц", "khmelnyts", "кам'янець-подільськ", "проскурів"]),
    ("Lviv",      ["львів", "lviv", "золоч", "перемишл", "бережан"]),
    ("Ivano-Frankivsk", ["івано-франків", "ivano-frank", "коломиї", "коломия",
                         "підгірян"]),
    ("Ternopil",  ["тернопіл", "ternopil"]),
    ("Zhytomyr",  ["житомир", "zhytomyr"]),
    ("Cherkasy",  ["черкас", "cherkasy"]),
    ("Mykolaiv",  ["миколаїв", "mykolaiv", "микільськ", "вознесенськ", "братськ"]),
    ("Volyn",     ["волин", "volyn"]),
    ("Rivne",     ["рівне", "rivne"]),
    ("Zakarpattia", ["закарпат"]),
    ("Chernivtsi", ["чернівц"]),
    ("Odesa",     ["одес"]),
    ("Kherson",   ["херсон"]),
    ("Dnipropetrovsk", ["дніпр", "катеринослав"]),
    ("Donetsk",   ["донецьк", "донеччин"]),
    ("Luhansk",   ["луганськ"]),
    ("Crimea",    ["ялта", "крим", "crimea", "сімферопол"]),
]

# Historical super-regions we'll fall back on if no oblast keyword hits
HISTORICAL_RULES = [
    ("Podillia (historical)", ["поділл", "podill"]),
    ("Galicia (historical)",  ["галичин", "galicia"]),
    ("Volhynia (historical)", ["волин", "volyn"]),
    ("Slobozhanshchyna (historical)", ["слобожан", "слобідськ"]),
]

# Filename-level region fallback: if metadata has no place info at all, use this.
FILENAME_REGION_FALLBACK = {
    "Dmytrenko_Yefremova_2014_Khmelnytsky_region__-_metadata.csv": "Khmelnytskyi",
    "Podillia_songs_-_metadata.csv": "Vinnytska",
    "Pisni_Zuikhy_1965_-_metadata.csv": "Vinnytska",
}


def extract_region(place: str) -> str:
    """Return a normalized region name or 'Unknown'."""
    if not isinstance(place, str) or not place.strip():
        return "Unknown"
    s = place.lower()
    for region, keywords in REGION_RULES:
        if any(kw in s for kw in keywords):
            return region
    for region, keywords in HISTORICAL_RULES:
        if any(kw in s for kw in keywords):
            return region
    return "Unknown"


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------
def _strip_bom(cols):
    return [c.strip().lstrip("\ufeff") for c in cols]


def read_metadata(path: Path, sep: str) -> pd.DataFrame:
    """Load a metadata CSV, drop fully-empty padding rows, strip BOM."""
    df = pd.read_csv(path, sep=sep, dtype=str, encoding="utf-8")
    df.columns = _strip_bom(df.columns)
    # Drop rows where song_id is missing — those are padding artifacts.
    df = df.dropna(subset=["song_id"]).copy()
    df["song_id"] = df["song_id"].str.strip()
    df = df[df["song_id"] != ""]
    # Some Skrypnyk files contain duplicate song_ids across rows. Keep first.
    df = df.drop_duplicates(subset=["song_id"], keep="first")
    return df


def read_texts(path: Path, sep: str) -> pd.DataFrame:
    """
    Load a text CSV safely (some files have hundreds of trailing empty columns)
    and aggregate to one row per song_id: joined full_text + line_count.
    """
    # Only keep the first 5 columns we care about. This avoids memory blowups
    # on files with spurious trailing delimiters.
    # We peek at the header first so we can adapt to `pos` vs `stanza/position`.
    head = pd.read_csv(path, sep=sep, nrows=0, encoding="utf-8")
    cols = _strip_bom(head.columns)

    # Normalize schema: target columns -> song_id, stanza, position, title, text
    if "pos" in cols and "stanza" not in cols:
        # Schema: song_id, pos, title, Text
        df = pd.read_csv(path, sep=sep, usecols=[0, 1, 2, 3], dtype=str,
                         names=["song_id", "position", "title", "text"],
                         header=0, encoding="utf-8")
        df["stanza"] = pd.NA
    else:
        # Schema: song_id, stanza, position, title, Text  (+ possibly empty cols)
        df = pd.read_csv(path, sep=sep, usecols=[0, 1, 2, 3, 4], dtype=str,
                         names=["song_id", "stanza", "position", "title", "text"],
                         header=0, encoding="utf-8")

    df.columns = _strip_bom(df.columns)
    df["song_id"] = df["song_id"].astype(str).str.strip()
    df = df[(df["song_id"] != "") & (df["song_id"].str.lower() != "nan")]

    # Sort by stanza/position so joined text is in reading order.
    for c in ("stanza", "position"):
        if c in df.columns:
            df[c + "_sort"] = pd.to_numeric(df[c], errors="coerce")
    sort_cols = [c for c in ("stanza_sort", "position_sort") if c in df.columns]
    if sort_cols:
        df = df.sort_values(["song_id"] + sort_cols, kind="stable")

    # Aggregate: join non-empty text lines with newline.
    def _join_lines(series):
        lines = [str(x).strip() for x in series if pd.notna(x) and str(x).strip()]
        return "\n".join(lines)

    def _first_non_null(series):
        for x in series:
            if pd.notna(x) and str(x).strip():
                return str(x).strip()
        return None

    agg = df.groupby("song_id", sort=False).agg(
        full_text=("text", _join_lines),
        title_from_text=("title", _first_non_null),
        line_count=("text", lambda s: sum(1 for x in s if pd.notna(x) and str(x).strip())),
    ).reset_index()
    return agg


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def build_dataset(input_dir: Path) -> pd.DataFrame:
    parts = []

    for meta_file, text_file, sep in FILE_PAIRS:
        meta_df = None
        text_df = None

        if meta_file is not None:
            meta_path = input_dir / meta_file
            if not meta_path.exists():
                print(f"  [skip] missing metadata file: {meta_file}", file=sys.stderr)
            else:
                meta_df = read_metadata(meta_path, sep)
                # Rename to English
                meta_df = meta_df.rename(columns=META_RENAME)

        if text_file is not None:
            text_path = input_dir / text_file
            if not text_path.exists():
                print(f"  [skip] missing text file: {text_file}", file=sys.stderr)
            else:
                text_df = read_texts(text_path, sep)

        # Merge this pair. Outer join on song_id so we never lose rows.
        if meta_df is not None and text_df is not None:
            merged = meta_df.merge(text_df, on="song_id", how="outer")
        elif meta_df is not None:
            merged = meta_df.copy()
            merged["full_text"] = pd.NA
            merged["title_from_text"] = pd.NA
            merged["line_count"] = 0
        else:
            merged = text_df.copy()
            merged["title"] = merged.get("title_from_text")

        # Record the source file(s)
        src_label = meta_file or text_file
        merged["source_file"] = src_label

        parts.append(merged)
        kept = len(merged)
        print(f"  [ok]   {src_label}: {kept} rows")

    combined = pd.concat(parts, ignore_index=True, sort=False)

    # ------------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------------
    # Make sure all expected columns exist
    for col in ["title", "genre", "year_recorded", "collector", "place_raw",
                "respondent", "respondent_age_or_birth_year",
                "full_text", "title_from_text", "line_count"]:
        if col not in combined.columns:
            combined[col] = pd.NA

    # Prefer metadata title; fall back to the title embedded in text rows.
    combined["title"] = combined["title"].where(
        combined["title"].notna() & (combined["title"].astype(str).str.strip() != ""),
        combined["title_from_text"],
    )

    # Country is fixed for this dataset
    combined["country"] = "Ukraine"

    # Region extraction
    combined["region"] = combined["place_raw"].apply(extract_region)

    # Filename-based fallback for sources with no place info
    mask = combined["region"] == "Unknown"
    for fname, region in FILENAME_REGION_FALLBACK.items():
        combined.loc[mask & (combined["source_file"] == fname), "region"] = region

    # Word count
    def _word_count(t):
        if not isinstance(t, str) or not t.strip():
            return 0
        return len(re.findall(r"\w+", t, flags=re.UNICODE))
    combined["word_count"] = combined["full_text"].apply(_word_count)

    # Fill numeric defaults
    combined["line_count"] = combined["line_count"].fillna(0).astype(int)

    # Final column order: everything the platform will actually use.
    final_cols = [
        "song_id",
        "title",
        "country",
        "region",
        "place_raw",
        "genre",
        "year_recorded",
        "collector",
        "respondent",
        "respondent_age_or_birth_year",
        "full_text",
        "line_count",
        "word_count",
        "source_file",
    ]
    combined = combined[final_cols]

    return combined


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", required=True,
                    help="Folder containing the Ukrainian song CSVs")
    ap.add_argument("--output", "-o", default="songs_merged.csv",
                    help="Output CSV path")
    args = ap.parse_args()

    input_dir = Path(args.input)
    if not input_dir.is_dir():
        print(f"ERROR: input folder not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading from: {input_dir}")
    df = build_dataset(input_dir)

    out_path = Path(args.output)
    df.to_csv(out_path, index=False, encoding="utf-8")

    # ------------------- summary -------------------
    print()
    print(f"Wrote {len(df)} rows to {out_path}")
    print(f"Unique song_ids: {df['song_id'].nunique()}")
    print()
    print("Rows per source_file:")
    print(df["source_file"].value_counts().to_string())
    print()
    print("Rows per region:")
    print(df["region"].value_counts().to_string())
    print()
    print("Text coverage:")
    has_text = df["full_text"].notna() & (df["full_text"].astype(str).str.strip() != "")
    print(f"  rows with full_text: {has_text.sum()} / {len(df)}")
    print(f"  median line_count (text-bearing rows): "
          f"{int(df.loc[has_text, 'line_count'].median())}")


if __name__ == "__main__":
    main()