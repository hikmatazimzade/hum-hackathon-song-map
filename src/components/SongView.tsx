"use client";

import { useMemo, type RefObject } from "react";
import type { Singer, Song } from "@/lib/types";
import {
  filterByVisibleSongs,
  isUnknownBucket,
  resolveSongs,
} from "@/lib/recommendations";

type Props = {
  song: Song;
  singer: Singer | null;
  songsById: Map<string, Song>;
  singersById: Map<string, Singer>;
  filteredSongIds: Set<string> | null;
  hasBack: boolean;
  scrollerRef: RefObject<HTMLDivElement | null>;
  onBack: () => void;
  onSelectSong: (song_id: string) => void;
};

function truncate(s: string, n: number): string {
  if (s.length <= n) return s;
  return s.slice(0, n - 1).trimEnd() + "…";
}

export function SongView({
  song,
  singer,
  songsById,
  singersById: _singersById,
  filteredSongIds,
  hasBack,
  scrollerRef,
  onBack,
  onSelectSong,
}: Props) {
  void _singersById;
  const singerIsUnknown = !singer || isUnknownBucket(singer);

  const { similars, usedUnfiltered } = useMemo(() => {
    const base = resolveSongs(song.similar_songs, songsById).filter(
      (s) => s.song_id !== song.song_id,
    );
    if (!filteredSongIds) {
      return { similars: base.slice(0, 5), usedUnfiltered: false };
    }
    const filt = filterByVisibleSongs(base, filteredSongIds);
    if (filt.length >= 3) {
      return { similars: filt.slice(0, 5), usedUnfiltered: false };
    }
    return { similars: base.slice(0, 5), usedUnfiltered: true };
  }, [song.similar_songs, song.song_id, songsById, filteredSongIds]);

  const moreFromSinger: Song[] = useMemo(() => {
    if (singerIsUnknown || !singer) return [];
    const others = singer.song_ids
      .filter((id) => id !== song.song_id)
      .map((id) => songsById.get(id))
      .filter((s): s is Song => !!s);
    return filterByVisibleSongs(others, filteredSongIds).slice(0, 5);
  }, [singer, singerIsUnknown, songsById, song.song_id, filteredSongIds]);

  return (
    <div className="flex h-full flex-col">
      <header className="flex-none px-6 pt-5 pb-4 border-b border-line-soft">
        {hasBack && (
          <button
            onClick={onBack}
            className="mb-2 inline-flex items-center gap-1.5 text-[10px] uppercase tracking-[0.15em] text-muted-soft hover:text-ink"
          >
            <svg width="9" height="9" viewBox="0 0 10 10" aria-hidden>
              <path
                d="M6.5 1L2.5 5l4 4"
                stroke="currentColor"
                strokeWidth="1.2"
                fill="none"
              />
            </svg>
            Back
          </button>
        )}
        <div className="eyebrow">Song</div>
        <h2 className="mt-1 font-serif text-[24px] leading-tight text-ink">
          {song.title || <span className="italic text-muted">Untitled</span>}
        </h2>
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-muted">
          {song.genre && <span>{song.genre}</span>}
          {song.genre && <Dot />}
          <span>{song.year ? song.year : "Year unknown"}</span>
          {song.collector && (
            <>
              <Dot />
              <span>coll. {song.collector}</span>
            </>
          )}
        </div>
        {song.place_raw && (
          <div className="mt-[2px] text-[11px] text-muted-soft">
            {song.place_raw}
          </div>
        )}
        <div className="mt-1 text-[11px] text-muted-soft">
          {song.line_count} lines · {song.word_count} words
        </div>
      </header>

      <div
        ref={scrollerRef as React.RefObject<HTMLDivElement>}
        className="paper-scroll min-h-0 flex-1 overflow-y-auto px-6 pt-4 pb-6"
      >
        {song.full_text ? (
          <div className="lyrics text-ink">{song.full_text}</div>
        ) : (
          <div className="italic text-muted">No text recorded.</div>
        )}

        <div className="mt-8">
          <div className="mb-2 flex items-baseline gap-2">
            <span className="eyebrow">Similar songs</span>
            {usedUnfiltered && (
              <span className="text-[10px] italic text-muted-soft">
                (showing without filters)
              </span>
            )}
          </div>
          {similars.length === 0 ? (
            <div className="text-[12px] italic text-muted">
              No similar songs in the current filtered set.
            </div>
          ) : (
            <ul className="flex flex-col">
              {similars.map((s, i) => (
                <li key={s.song_id}>
                  <button
                    onClick={() => onSelectSong(s.song_id)}
                    className={`group relative flex w-full items-baseline gap-3 py-[10px] text-left transition-colors hover:bg-[#f1e8d7] ${
                      i < similars.length - 1
                        ? "border-b border-line-soft"
                        : ""
                    }`}
                  >
                    <span
                      aria-hidden
                      className="absolute left-0 top-2 bottom-2 w-[2px] bg-accent-medium opacity-0 transition-opacity group-hover:opacity-100"
                    />
                    <span className="min-w-0 truncate pl-3 text-[13px] text-ink">
                      {truncate(s.title || "Untitled", 45)}
                      {s.oblast && (
                        <span className="text-muted-soft"> · {s.oblast}</span>
                      )}
                      {s.genre && (
                        <span className="text-muted-soft">
                          {" · "}
                          {truncate(s.genre, 20)}
                        </span>
                      )}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {moreFromSinger.length > 0 && (
          <div className="mt-6">
            <div className="eyebrow mb-2">More from this singer</div>
            <ul className="flex flex-col">
              {moreFromSinger.map((s, i) => (
                <li key={s.song_id}>
                  <button
                    onClick={() => onSelectSong(s.song_id)}
                    className={`group relative flex w-full items-baseline gap-3 py-[10px] text-left transition-colors hover:bg-[#f1e8d7] ${
                      i < moreFromSinger.length - 1
                        ? "border-b border-line-soft"
                        : ""
                    }`}
                  >
                    <span
                      aria-hidden
                      className="absolute left-0 top-2 bottom-2 w-[2px] bg-accent-medium opacity-0 transition-opacity group-hover:opacity-100"
                    />
                    <span className="min-w-0 truncate pl-3 text-[13px] text-ink">
                      {truncate(s.title || "Untitled", 45)}
                      {s.genre && (
                        <span className="text-muted-soft">
                          {" · "}
                          {truncate(s.genre, 20)}
                        </span>
                      )}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function Dot() {
  return (
    <span
      aria-hidden
      className="inline-block h-[3px] w-[3px] rounded-full bg-muted-soft/60"
    />
  );
}
