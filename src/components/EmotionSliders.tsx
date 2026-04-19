"use client";

import { RangeSlider, type RangeValue } from "@/lib/range-slider";

export const FULL_RANGE: RangeValue = { min: -1, max: 1 };

export function isFullRange(v: RangeValue): boolean {
  return v.min <= -1 + 1e-9 && v.max >= 1 - 1e-9;
}

type Props = {
  tone: RangeValue;
  energy: RangeValue;
  onToneChange: (v: RangeValue) => void;
  onEnergyChange: (v: RangeValue) => void;
  onReset: () => void;
  count: number;
};

export function EmotionSliders({
  tone,
  energy,
  onToneChange,
  onEnergyChange,
  onReset,
  count,
}: Props) {
  const active = !isFullRange(tone) || !isFullRange(energy);
  const empty = count === 0;
  const tight = !empty && count < 20;

  const countText = empty ? "No matches" : count.toLocaleString();
  const countClass = empty || tight ? "text-accent-medium" : "text-muted-soft";

  return (
    <div className="px-5">
      <div className="mb-2 flex items-baseline justify-between">
        <span className="eyebrow">Emotion</span>
        <button
          onClick={onReset}
          disabled={!active}
          className={`text-[11px] uppercase tracking-wider transition-colors ${
            active ? "text-muted-soft hover:text-accent-medium" : "invisible"
          }`}>
          Reset
        </button>
      </div>

      <div className="flex flex-col gap-3">
        <div>
          <div className="flex items-baseline justify-between">
            <span className="text-[12px] text-ink">Tone</span>
            <span
              className={`text-[11px] tabular-nums ${countClass}`}
              aria-live="polite">
              {countText}
            </span>
          </div>
          <RangeSlider
            value={tone}
            onChange={onToneChange}
            domain={[-1, 1]}
            step={0.1}
            leftLabel="sad"
            rightLabel="happy"
            ariaLabel="Tone range, from sad to happy"
          />
        </div>

        <div>
          <div className="flex items-baseline justify-between">
            <span className="text-[12px] text-ink">Intensity</span>
            <span
              className={`text-[11px] tabular-nums ${countClass}`}
              aria-live="polite">
              {countText}
            </span>
          </div>
          <RangeSlider
            value={energy}
            onChange={onEnergyChange}
            domain={[-1, 1]}
            step={0.1}
            leftLabel="calm"
            rightLabel="intense"
            ariaLabel="Energy range, from calm to intense"
          />
        </div>

        {empty && (
          <div className="text-[11px] italic leading-snug text-accent-medium">
            Try widening the range or clearing other filters.
          </div>
        )}
      </div>
    </div>
  );
}
