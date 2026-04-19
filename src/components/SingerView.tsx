"use client";

import { useMemo, type RefObject } from "react";
import type { Singer, Song } from "@/lib/types";
import {
  filterSingersByVisibleSongs,
  isUnknownBucket,
  resolveNamedSingers,
} from "@/lib/recommendations";

type Props = {
  singer: Singer;
  songs: Song[];
  filtered: boolean;
  totalSongCount: number;
  singersById: Map<string, Singer>;
  filteredSongIds: Set<string> | null;
  hasBack: boolean;
  scrollerRef: RefObject<HTMLDivElement | null>;
  onBack: () => void;
  onSelectSong: (song_id: string) => void;
  onSelectSinger: (singer_id: string) => void;
};

export function SingerView({
  singer,
  songs,
  filtered,
  totalSongCount,
  singersById,
  filteredSongIds,
  hasBack,
  scrollerRef,
  onBack,
  onSelectSong,
  onSelectSinger,
}: Props) {
  const isUnknown = isUnknownBucket(singer);

  const { similars, usedUnfiltered } = useMemo(() => {
    const base = resolveNamedSingers(singer.similar_singers, singersById);
    if (!filteredSongIds) {
      return { similars: base.slice(0, 5), usedUnfiltered: false };
    }
    const filt = filterSingersByVisibleSongs(base, filteredSongIds);
    if (filt.length >= 3) {
      return { similars: filt.slice(0, 5), usedUnfiltered: false };
    }
    return { similars: base.slice(0, 5), usedUnfiltered: true };
  }, [singer.similar_singers, singersById, filteredSongIds]);

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
        <div className="eyebrow">Singer</div>
        <h2
          className={`mt-1 font-serif text-[28px] leading-tight ${
            isUnknown ? "italic text-muted" : "text-ink"
          }`}
        >
          {isUnknown ? `Unattributed songs — ${singer.region}` : singer.name}
        </h2>
        <div className="mt-1 flex items-center gap-2 text-[13px] text-muted">
          {singer.role && (
            <>
              <span className="italic">{singer.role}</span>
              <span
                aria-hidden
                className="inline-block h-[4px] w-[4px] rounded-full bg-accent-medium"
              />
            </>
          )}
          <span>{singer.region}</span>
          <span
            aria-hidden
            className="inline-block h-[4px] w-[4px] rounded-full bg-accent-medium"
          />
          <span>
            {filtered ? (
              <>
                {songs.length} of {totalSongCount} song
                {totalSongCount === 1 ? "" : "s"} in filter
              </>
            ) : (
              <>
                {singer.song_count} song{singer.song_count === 1 ? "" : "s"}
              </>
            )}
          </span>
        </div>
      </header>

      <div
        ref={scrollerRef as React.RefObject<HTMLDivElement>}
        className="paper-scroll min-h-0 flex-1 overflow-y-auto px-6 pt-4 pb-6"
      >
        <div className="eyebrow mb-2">Songs</div>
        {songs.length === 0 ? (
          <div className="text-[13px] italic text-muted">
            No songs match the current filters.
          </div>
        ) : (
          <ul className="flex flex-col">
            {songs.map((song, i) => (
              <li key={song.song_id}>
                <button
                  onClick={() => onSelectSong(song.song_id)}
                  className={`group relative flex w-full items-baseline gap-3 py-[12px] text-left transition-colors hover:bg-[#f1e8d7] ${
                    i < songs.length - 1 ? "border-b border-line-soft" : ""
                  }`}
                >
                  <span
                    aria-hidden
                    className="absolute left-0 top-2 bottom-2 w-[2px] bg-accent-medium opacity-0 transition-opacity group-hover:opacity-100"
                  />
                  <div className="min-w-0 pl-3">
                    <div className="truncate font-serif text-[15px] text-ink">
                      {song.title || (
                        <span className="italic text-muted">Untitled</span>
                      )}
                    </div>
                    <div className="mt-[2px] text-[11px] text-muted-soft">
                      {song.genre ?? "—"}
                      {song.year && <> · {song.year}</>}
                      {song.line_count > 0 && <> · {song.line_count} lines</>}
                    </div>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}

        {!isUnknown && (
          <div className="mt-8">
            <div className="mb-2 flex items-baseline gap-2">
              <span className="eyebrow">Similar singers</span>
              {usedUnfiltered && (
                <span className="text-[10px] italic text-muted-soft">
                  (showing without filters)
                </span>
              )}
            </div>
            {similars.length === 0 ? (
              <div className="text-[12px] italic text-muted">
                No similar singers identified.
              </div>
            ) : (
              <ul className="flex flex-col">
                {similars.map((s, i) => (
                  <li key={s.singer_id}>
                    <button
                      onClick={() => onSelectSinger(s.singer_id)}
                      className={`group relative flex w-full items-baseline justify-between gap-3 py-[10px] text-left transition-colors hover:bg-[#f1e8d7] ${
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
                        {s.name}
                        {s.role && (
                          <span className="ml-[6px] text-[11px] italic text-muted-soft">
                            {s.role}
                          </span>
                        )}
                        <span className="ml-[6px] text-[11px] text-muted-soft">
                          · {s.region}
                        </span>
                      </span>
                      <span className="shrink-0 text-[11px] tabular-nums text-muted-soft">
                        {s.song_count}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
