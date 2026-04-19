"use client";

import type { Theme } from "@/lib/types";
import { densityFraction } from "@/lib/density-scale";

type Props = {
  themes: Theme[];
  // Count of songs with each theme in the CURRENT view. When nothing is
  // selected this should equal themes.json's song_count.
  counts: Record<string, number>;
  selected: Set<string>;
  onToggle: (themeId: string) => void;
  onClear: () => void;
};

export function ThemesPanel({
  themes,
  counts,
  selected,
  onToggle,
  onClear,
}: Props) {
  const hasSelection = selected.size > 0;
  const shown = themes.map((t) => ({
    ...t,
    display_count: counts[t.id] ?? 0,
  }));
  const maxCount = Math.max(1, ...shown.map((t) => t.display_count));

  return (
    <div className="flex flex-col px-5">
      <div className="mb-3 flex items-baseline justify-between">
        <span className="eyebrow">Themes</span>
        <button
          onClick={onClear}
          disabled={!hasSelection}
          className={`text-[11px] uppercase tracking-wider transition-colors ${
            hasSelection
              ? "text-muted-soft hover:text-accent-medium"
              : "invisible"
          }`}
        >
          Clear
        </button>
      </div>

      <div className="flex flex-col gap-[6px]">
        {shown.map((t) => {
          const isSelected = selected.has(t.id);
          const frac = densityFraction(t.display_count, maxCount);
          const rowOpacity = hasSelection && !isSelected ? 0.55 : 1;

          return (
            <button
              key={t.id}
              onClick={() => onToggle(t.id)}
              aria-pressed={isSelected}
              className="group relative block w-full py-[6px] text-left"
              style={{ opacity: rowOpacity, minHeight: 36 }}
            >
              {isSelected && (
                <span
                  aria-hidden
                  className="absolute -left-2 top-1 bottom-1 w-[2px] rounded-sm bg-accent-medium"
                />
              )}
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-[13px] leading-none text-ink">
                  {t.label}
                </span>
                <span className="text-[11px] leading-none tabular-nums text-muted-soft">
                  {t.display_count.toLocaleString()}
                </span>
              </div>
              <div className="mt-[5px] h-[3px] w-full overflow-hidden rounded-full bg-[#eadbc3]">
                <div
                  className="h-full rounded-full bg-accent-medium"
                  style={{
                    width: `${Math.max(2, frac * 100)}%`,
                    transition:
                      "width 180ms ease, background-color 180ms ease",
                  }}
                />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
