"use client";

import type { RefObject } from "react";
import type { Region, Singer } from "@/lib/types";

type Props = {
  region: Region;
  singers: Singer[];
  filteredSongs: Set<string> | null;
  unattributedCount: number;
  scrollerRef: RefObject<HTMLDivElement | null>;
  onSelectSinger: (singer_id: string) => void;
  onSelectUnattributedList: () => void;
};

export function RegionView({
  region,
  singers,
  filteredSongs,
  unattributedCount,
  scrollerRef,
  onSelectSinger,
  onSelectUnattributedList,
}: Props) {
  const songCountFor = (s: Singer) =>
    filteredSongs
      ? s.song_ids.filter((id) => filteredSongs.has(id)).length
      : s.song_count;

  return (
    <div className="flex h-full flex-col">
      {/* Fixed detail header */}
      <header className="flex-none px-6 pt-5 pb-4 border-b border-line-soft">
        <div className="eyebrow">Region</div>
        <h2 className="mt-1 font-serif text-[32px] leading-tight text-ink">
          {region.region}
        </h2>
        <div className="mt-1 flex items-center gap-2 text-[13px] text-muted">
          <span>
            {region.song_count.toLocaleString()} song
            {region.song_count === 1 ? "" : "s"}
          </span>
          <span
            aria-hidden
            className="inline-block h-[4px] w-[4px] rounded-full bg-accent-medium"
          />
          <span>
            {region.singer_count} singer
            {region.singer_count === 1 ? "" : "s"}
          </span>
        </div>
      </header>

      {/* Scrollable singer list */}
      <div
        ref={scrollerRef as React.RefObject<HTMLDivElement>}
        className="paper-scroll min-h-0 flex-1 overflow-y-auto px-6 pt-4 pb-6"
      >
        {singers.length === 0 && unattributedCount === 0 ? (
          <div className="text-sm italic leading-relaxed text-muted">
            No singers match the current filters.
          </div>
        ) : (
          <>
            {singers.length > 0 && (
              <>
                <div className="eyebrow mb-2">Singers</div>
                <ul className="flex flex-col">
                  {singers.map((s, i) => (
                    <li key={s.singer_id}>
                      <button
                        onClick={() => onSelectSinger(s.singer_id)}
                        className={`group relative flex w-full items-baseline justify-between gap-4 py-[14px] text-left transition-colors hover:bg-[#f1e8d7] ${
                          i < singers.length - 1
                            ? "border-b border-line-soft"
                            : ""
                        }`}
                        style={{ minHeight: 52 }}
                      >
                        <span
                          aria-hidden
                          className="absolute left-0 top-2 bottom-2 w-[2px] bg-accent-medium opacity-0 transition-opacity group-hover:opacity-100"
                        />
                        <span className="min-w-0 truncate pl-3 text-[15px] text-ink">
                          <span>{s.name}</span>
                          {s.role && (
                            <span className="ml-[6px] text-[11px] italic text-muted-soft">
                              {s.role}
                            </span>
                          )}
                          <span className="ml-[6px] text-[11px] text-muted-soft">
                            · {s.region}
                          </span>
                        </span>
                        <span className="shrink-0 text-[12px] tabular-nums text-muted-soft">
                          {songCountFor(s)}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}
            {unattributedCount > 0 && (
              <button
                onClick={onSelectUnattributedList}
                className="mt-4 text-left text-[12px] text-muted-soft hover:text-ink"
              >
                + {unattributedCount.toLocaleString()} song
                {unattributedCount === 1 ? "" : "s"} without singer
                attribution
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
