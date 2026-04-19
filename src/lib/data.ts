import type {
  OblastFeatureCollection,
  Region,
  Singer,
  Song,
  Theme,
} from "./types";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return (await res.json()) as T;
}

export async function loadAll() {
  const [songs, singers, regions, themes, geojson] = await Promise.all([
    fetchJson<Song[]>("/data/songs.json"),
    fetchJson<Singer[]>("/data/singers.json"),
    fetchJson<Region[]>("/data/regions.json"),
    fetchJson<Theme[]>("/data/themes.json"),
    fetchJson<OblastFeatureCollection>(
      "/data/ukraine_ethno_regions.geojson",
    ).catch(() => null),
  ]);
  return { songs, singers, regions, themes, geojson };
}

export function indexById<T extends { [k: string]: unknown }>(
  rows: T[],
  key: keyof T,
): Map<string, T> {
  const m = new Map<string, T>();
  for (const r of rows) m.set(r[key] as unknown as string, r);
  return m;
}
