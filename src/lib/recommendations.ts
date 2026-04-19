import type { Singer, Song } from "./types";

// An unknown-bucket singer is an aggregation shim for region+null-respondent
// songs (e.g. singer_id "vinnytska--" or "poltava--unknown"). They have
// empty/null `name`. We never surface them as clickable named entities.
export function isUnknownBucket(s: Pick<Singer, "name" | "singer_id">): boolean {
  if (!s.name || !s.name.trim()) return true;
  if (s.singer_id.endsWith("--unknown")) return true;
  return false;
}

// Resolve a list of song_ids to full Song objects, preserving source order.
export function resolveSongs(ids: string[], byId: Map<string, Song>): Song[] {
  const out: Song[] = [];
  for (const id of ids) {
    const s = byId.get(id);
    if (s) out.push(s);
  }
  return out;
}

// Resolve a list of singer_ids to Singer objects, skipping unknown buckets
// and missing entries, preserving source order.
export function resolveNamedSingers(
  ids: string[],
  byId: Map<string, Singer>,
): Singer[] {
  const out: Singer[] = [];
  for (const id of ids) {
    const s = byId.get(id);
    if (!s || isUnknownBucket(s)) continue;
    out.push(s);
  }
  return out;
}

// Recommendation filtering: apply the active theme/emotion filter
// (represented here as a set of song_ids already determined by page.tsx).
// If filteredIds is null, no filter is active — return items unchanged.
export function filterByVisibleSongs<T extends Song>(
  items: T[],
  filteredIds: Set<string> | null,
): T[] {
  if (!filteredIds) return items;
  return items.filter((i) => filteredIds.has(i.song_id));
}

// For singers, "pass the filter" means having at least one visible song.
export function filterSingersByVisibleSongs(
  singers: Singer[],
  filteredIds: Set<string> | null,
): Singer[] {
  if (!filteredIds) return singers;
  return singers.filter((s) => s.song_ids.some((id) => filteredIds.has(id)));
}
