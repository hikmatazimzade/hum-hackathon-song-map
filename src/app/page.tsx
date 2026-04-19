"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import { loadAll } from "@/lib/data";
import type {
  Country,
  NavEntry,
  OblastFeatureCollection,
  Region,
  Singer,
  Song,
  Theme,
} from "@/lib/types";
import { RightPanel } from "@/components/RightPanel";
import { ThemesPanel } from "@/components/ThemesPanel";
import {
  EmotionSliders,
  FULL_RANGE,
  isFullRange,
} from "@/components/EmotionSliders";
import type { RangeValue } from "@/lib/range-slider";
import { ethnoForOblast } from "@/lib/oblasts";

const RegionMap = dynamic(
  () => import("@/components/Map").then((m) => m.RegionMap),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center text-sm text-muted">
        Loading map&hellip;
      </div>
    ),
  },
);

type LoadedData = {
  songs: Song[];
  singers: Singer[];
  regions: Region[];
  themes: Theme[];
  geojson: OblastFeatureCollection | null;
};

const MAX_STACK = 10;

function entryToHash(e: NavEntry): string {
  if (e.kind === "region") return `#/region/${encodeURIComponent(e.region)}`;
  if (e.kind === "singer") return `#/singer/${encodeURIComponent(e.singer_id)}`;
  return `#/song/${encodeURIComponent(e.song_id)}`;
}

function hashToEntry(h: string): NavEntry | null {
  if (!h.startsWith("#/")) return null;
  const rest = h.slice(2);
  const slash = rest.indexOf("/");
  if (slash < 0) return null;
  const kind = rest.slice(0, slash);
  const id = decodeURIComponent(rest.slice(slash + 1));
  if (!id) return null;
  if (kind === "region") return { kind: "region", region: id };
  if (kind === "singer") return { kind: "singer", singer_id: id };
  if (kind === "song") return { kind: "song", song_id: id };
  return null;
}

export default function Page() {
  const [country, setCountry] = useState<Country>("Ukraine");
  const [data, setData] = useState<LoadedData | null>(null);
  const [stack, setStack] = useState<NavEntry[]>([]);
  const [selectedThemes, setSelectedThemes] = useState<Set<string>>(new Set());
  const [tone, setTone] = useState<RangeValue>(FULL_RANGE);
  const [energy, setEnergy] = useState<RangeValue>(FULL_RANGE);

  useEffect(() => {
    loadAll()
      .then((d) => {
        setData(d);
        // Seed the stack from the URL hash on first load so deep links work.
        if (typeof window !== "undefined") {
          const entry = hashToEntry(window.location.hash);
          if (entry) setStack([entry]);
        }
      })
      .catch((e) => {
        console.error("failed to load data", e);
      });
  }, []);

  // Keep location.hash in sync with the top of the stack.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const top = stack[stack.length - 1];
    const desired = top ? entryToHash(top) : "#";
    if (window.location.hash !== desired) {
      // replaceState — we own our own stack; no need to flood browser history.
      history.replaceState(null, "", desired);
    }
  }, [stack]);

  // Respond to user-driven hash changes (e.g. back/forward) by replacing
  // the stack with [hash-entry] (we don't try to reconstruct history).
  useEffect(() => {
    function onHash() {
      const entry = hashToEntry(window.location.hash);
      setStack(entry ? [entry] : []);
    }
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const push = useCallback((e: NavEntry) => {
    setStack((prev) => [...prev, e].slice(-MAX_STACK));
  }, []);
  const pop = useCallback(() => {
    setStack((prev) => prev.slice(0, -1));
  }, []);
  const resetTo = useCallback((e: NavEntry) => {
    setStack([e]);
  }, []);

  const maps = useMemo(() => {
    if (!data) return null;
    const regionMap = new Map(data.regions.map((r) => [r.region, r]));
    const singerMap = new Map(data.singers.map((s) => [s.singer_id, s]));
    const songMap = new Map(data.songs.map((s) => [s.song_id, s]));

    // Group singers by ethnographic region. singer.region is oblast-level
    // (Poltava, Kyiv, …); we look up its ethno via OBLAST_TO_ETHNO, with
    // special-case "Podillia (historical)" → "Podillia".
    const singersByRegion = new Map<string, Singer[]>();
    for (const s of data.singers) {
      const ethno =
        s.region === "Podillia (historical)"
          ? "Podillia"
          : ethnoForOblast(s.region);
      if (!ethno) continue;
      const list = singersByRegion.get(ethno) ?? [];
      list.push(s);
      singersByRegion.set(ethno, list);
    }
    for (const list of singersByRegion.values()) {
      list.sort((a, b) => b.song_count - a.song_count);
    }
    return { regionMap, singerMap, songMap, singersByRegion };
  }, [data]);

  const { filteredSongs, filteredRegionCounts, themeCounts, filteredCount } =
    useMemo(() => {
      if (!data) {
        return {
          filteredSongs: null as Set<string> | null,
          filteredRegionCounts: null as Map<string, number> | null,
          themeCounts: {} as Record<string, number>,
          filteredCount: 0,
        };
      }

      const themesActive = selectedThemes.size > 0;
      const emotionActive = !isFullRange(tone) || !isFullRange(energy);
      const anyFilter = themesActive || emotionActive;

      const visible: Song[] = anyFilter
        ? data.songs.filter((s) => {
            if (themesActive && !s.themes.some((t) => selectedThemes.has(t))) {
              return false;
            }
            if (emotionActive) {
              if (s.valence < tone.min || s.valence > tone.max) return false;
              if (s.arousal < energy.min || s.arousal > energy.max) return false;
            }
            return true;
          })
        : data.songs;

      const counts: Record<string, number> = {};
      if (anyFilter) {
        for (const t of data.themes) counts[t.id] = 0;
        for (const s of visible) {
          for (const t of s.themes) {
            if (counts[t] !== undefined) counts[t]++;
          }
        }
      } else {
        for (const t of data.themes) counts[t.id] = t.song_count;
      }

      const filteredSet = anyFilter
        ? new Set(visible.map((s) => s.song_id))
        : null;

      const regionCounts = new Map<string, number>();
      if (anyFilter) {
        for (const r of data.regions) regionCounts.set(r.region, 0);
        for (const s of visible) {
          if (s.region) {
            regionCounts.set(s.region, (regionCounts.get(s.region) ?? 0) + 1);
          }
        }
      }

      return {
        filteredSongs: filteredSet,
        filteredRegionCounts: anyFilter ? regionCounts : null,
        themeCounts: counts,
        filteredCount: anyFilter ? visible.length : data.songs.length,
      };
    }, [data, selectedThemes, tone, energy]);

  const toggleTheme = (id: string) => {
    setSelectedThemes((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const top = stack.length > 0 ? stack[stack.length - 1] : null;
  const selectedRegionName =
    top?.kind === "region"
      ? top.region
      : top?.kind === "singer"
      ? (() => {
          const s = maps?.singerMap.get(top.singer_id);
          if (!s) return null;
          return s.region === "Podillia (historical)"
            ? "Podillia"
            : ethnoForOblast(s.region);
        })()
      : top?.kind === "song"
      ? (() => {
          const song = maps?.songMap.get(top.song_id);
          return song?.region ?? null;
        })()
      : null;

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-paper">
      {/* Header — fixed 56px */}
      <header className="flex h-14 flex-none items-center justify-between border-b border-line-soft px-6">
        <div className="flex items-baseline gap-3">
          <h1 className="font-serif text-[20px] leading-none tracking-tight text-ink">
            Song Map
          </h1>
          <span className="text-[10px] uppercase tracking-[0.12em] text-muted-soft">
            folk songs archive
          </span>
          <span
            aria-hidden
            className="mx-1 inline-block h-1 w-1 rounded-full bg-muted-soft/60"
          />
          <div className="flex overflow-hidden rounded-full border border-line-soft text-[12px]">
            {(["Ukraine", "Estonia"] as const).map((c) => (
              <button
                key={c}
                onClick={() => {
                  setCountry(c);
                  setStack([]);
                }}
                className={`h-8 px-3.5 leading-none ${
                  country === c
                    ? "bg-ink-strong text-paper"
                    : "bg-transparent text-muted hover:text-ink"
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2 text-[12px] text-muted-soft">
          <svg
            width="12"
            height="12"
            viewBox="0 0 12 12"
            aria-hidden
            className="stroke-muted-soft"
            fill="none"
          >
            <circle cx="5.2" cy="5.2" r="3.4" strokeWidth="1.2" />
            <path d="M7.7 7.7L10 10" strokeWidth="1.2" strokeLinecap="round" />
          </svg>
          <span>Search singers, songs…</span>
        </div>
      </header>

      {/* Body */}
      <div className="flex min-h-0 flex-1 overflow-hidden">
        {/* Left panel */}
        <aside className="flex w-[280px] flex-none flex-col overflow-hidden border-r border-line-soft bg-card">
          {country === "Ukraine" && data ? (
            <>
              <div className="paper-scroll min-h-0 flex-1 overflow-y-auto pt-5">
                <ThemesPanel
                  themes={data.themes}
                  counts={themeCounts}
                  selected={selectedThemes}
                  onToggle={toggleTheme}
                  onClear={() => setSelectedThemes(new Set())}
                />
              </div>
              <div className="flex-none border-t border-line-soft pb-4 pt-4">
                <EmotionSliders
                  tone={tone}
                  energy={energy}
                  onToneChange={setTone}
                  onEnergyChange={setEnergy}
                  onReset={() => {
                    setTone(FULL_RANGE);
                    setEnergy(FULL_RANGE);
                  }}
                  count={filteredCount}
                />
              </div>
            </>
          ) : (
            <div className="px-5 pt-5 eyebrow">Themes</div>
          )}
        </aside>

        {/* Map */}
        <main className="map-container relative min-h-0 min-w-0 flex-1">
          {country === "Estonia" ? (
            <div className="flex h-full items-center justify-center p-12">
              <div className="max-w-md space-y-3 rounded-sm border border-line-soft bg-white/40 p-8 text-center">
                <div className="font-serif text-2xl text-ink">
                  Estonian data coming soon
                </div>
                <p className="text-sm leading-relaxed text-muted">
                  The archive will extend to Estonian regilaul. The pipeline
                  is country-agnostic; only the data is missing for now.
                </p>
              </div>
            </div>
          ) : data && maps ? (
            <RegionMap
              regions={data.regions}
              geojson={data.geojson}
              selectedRegion={selectedRegionName ?? null}
              onSelectRegion={(region) =>
                resetTo({ kind: "region", region })
              }
              regionCountOverrides={filteredRegionCounts}
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-muted">
              Loading&hellip;
            </div>
          )}
        </main>

        {/* Right panel */}
        <aside className="flex w-[380px] flex-none flex-col overflow-hidden border-l border-line-soft bg-card">
          {country === "Estonia" ? (
            <div className="flex h-full items-center justify-center p-8 text-center text-sm text-muted">
              No data yet.
            </div>
          ) : data && maps ? (
            <RightPanel
              top={top}
              regions={maps.regionMap}
              singers={maps.singerMap}
              songs={maps.songMap}
              singersByRegion={maps.singersByRegion}
              filteredSongs={filteredSongs}
              hasBack={stack.length > 1}
              onSelectRegion={(region) => push({ kind: "region", region })}
              onSelectSinger={(singer_id) =>
                push({ kind: "singer", singer_id })
              }
              onSelectSong={(song_id) => push({ kind: "song", song_id })}
              onBack={pop}
            />
          ) : null}
        </aside>
      </div>
    </div>
  );
}
