"use client";

import { useEffect, useRef } from "react";
import type { NavEntry, Region, Singer, Song } from "@/lib/types";
import { RegionView } from "./RegionView";
import { SingerView } from "./SingerView";
import { SongView } from "./SongView";
import { isUnknownBucket } from "@/lib/recommendations";

type Props = {
  top: NavEntry | null;
  regions: Map<string, Region>;
  singers: Map<string, Singer>;
  songs: Map<string, Song>;
  singersByRegion: Map<string, Singer[]>;
  filteredSongs: Set<string> | null;
  hasBack: boolean;
  onSelectRegion: (region: string) => void;
  onSelectSinger: (singer_id: string) => void;
  onSelectSong: (song_id: string) => void;
  onBack: () => void;
};

export function RightPanel(p: Props) {
  // Scroll each sub-view's scroller to top on nav transition.
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const key = p.top
    ? p.top.kind === "region"
      ? `r:${p.top.region}`
      : p.top.kind === "singer"
      ? `s:${p.top.singer_id}`
      : `S:${p.top.song_id}`
    : "none";
  useEffect(() => {
    if (scrollerRef.current) scrollerRef.current.scrollTop = 0;
  }, [key]);

  if (!p.top) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-8 text-center">
        <div className="max-w-xs space-y-2">
          <div className="font-serif text-xl text-ink">
            Click a region to begin
          </div>
          <p className="text-sm leading-relaxed text-muted">
            The map shows seven ethnographic regions of Ukraine. Darker
            fills carry more songs.
          </p>
        </div>
      </div>
    );
  }

  if (p.top.kind === "region") {
    const region = p.regions.get(p.top.region);
    if (!region) return null;
    const allSingers = p.singersByRegion.get(region.region) ?? [];
    const named = allSingers.filter((s) => !isUnknownBucket(s));
    const singers = p.filteredSongs
      ? named.filter((s) =>
          s.song_ids.some((id) => p.filteredSongs!.has(id)),
        )
      : named;
    let unattributedCount = 0;
    let unknownBucket: Singer | null = null;
    for (const s of allSingers) {
      if (!isUnknownBucket(s)) continue;
      unknownBucket ??= s;
      for (const id of s.song_ids) {
        if (p.filteredSongs && !p.filteredSongs.has(id)) continue;
        unattributedCount++;
      }
    }
    return (
      <RegionView
        region={region}
        singers={singers}
        filteredSongs={p.filteredSongs}
        unattributedCount={unattributedCount}
        scrollerRef={scrollerRef}
        onSelectSinger={p.onSelectSinger}
        onSelectUnattributedList={() => {
          if (unknownBucket) p.onSelectSinger(unknownBucket.singer_id);
        }}
      />
    );
  }

  if (p.top.kind === "singer") {
    const singer = p.singers.get(p.top.singer_id);
    if (!singer) return null;
    const allSongs = singer.song_ids
      .map((id) => p.songs.get(id))
      .filter((s): s is Song => !!s);
    const songs = p.filteredSongs
      ? allSongs.filter((s) => p.filteredSongs!.has(s.song_id))
      : allSongs;
    return (
      <SingerView
        singer={singer}
        songs={songs}
        filtered={!!p.filteredSongs}
        totalSongCount={allSongs.length}
        singersById={p.singers}
        filteredSongIds={p.filteredSongs}
        hasBack={p.hasBack}
        scrollerRef={scrollerRef}
        onBack={p.onBack}
        onSelectSong={p.onSelectSong}
        onSelectSinger={p.onSelectSinger}
      />
    );
  }

  // song
  const song = p.songs.get(p.top.song_id);
  if (!song) return null;
  const singer = p.singers.get(song.singer_id) ?? null;
  return (
    <SongView
      song={song}
      singer={singer}
      songsById={p.songs}
      singersById={p.singers}
      filteredSongIds={p.filteredSongs}
      hasBack={p.hasBack}
      scrollerRef={scrollerRef}
      onBack={p.onBack}
      onSelectSong={p.onSelectSong}
    />
  );
}
