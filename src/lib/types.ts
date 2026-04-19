export type Country = "Ukraine" | "Estonia";

export type Song = {
  song_id: string;
  title: string | null;
  region: string | null;
  oblast: string | null;
  country: string;
  genre: string | null;
  year: number | null;
  year_raw: string | null;
  collector: string | null;
  singer_id: string;
  singer_name: string | null;
  singer_role: string | null;
  line_count: number;
  word_count: number;
  full_text: string;
  place_raw: string | null;
  themes: string[];
  primary_theme: string | null;
  valence: number;
  arousal: number;
  similar_songs: string[];
};

export type Theme = {
  id: string;
  label: string;
  song_count: number;
  primary_count: number;
};

export type Singer = {
  singer_id: string;
  name: string | null;
  role: string | null;
  region: string; // oblast-level, e.g. "Poltava"
  country: string;
  song_count: number;
  song_ids: string[];
  similar_singers: string[];
};

export type Region = {
  region: string;
  country: string;
  song_count: number;
  singer_count: number;
  centroid: [number, number];
  bbox: [[number, number], [number, number]];
};

export type RegionFeatureProps = {
  region: string;
  label_lng?: number;
  label_lat?: number;
  name_uk?: string | null;
};

export type OblastFeature = GeoJSON.Feature<GeoJSON.Geometry, RegionFeatureProps>;

export type OblastFeatureCollection = GeoJSON.FeatureCollection<GeoJSON.Geometry, RegionFeatureProps>;

export type NavEntry =
  | { kind: "region"; region: string }
  | { kind: "singer"; singer_id: string }
  | { kind: "song"; song_id: string };
