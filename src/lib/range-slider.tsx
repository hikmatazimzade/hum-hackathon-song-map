"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";

export type RangeValue = { min: number; max: number };

type Props = {
  value: RangeValue;
  onChange: (v: RangeValue) => void;
  domain: [number, number];
  step: number;
  leftLabel: string;
  rightLabel: string;
  ariaLabel: string; // describes the whole track
};

function snap(v: number, step: number, domainMin: number): number {
  // Snap to `step` grid anchored at domainMin (so -1.0, -0.9, …, +1.0).
  const n = Math.round((v - domainMin) / step);
  return +(domainMin + n * step).toFixed(10);
}

function clamp(v: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, v));
}

function formatSigned(v: number): string {
  // Always show sign, one decimal place.
  const n = +v.toFixed(1);
  if (n > 0) return `+${n.toFixed(1)}`;
  if (n < 0) return n.toFixed(1); // includes "-"
  return "+0.0";
}

export function RangeSlider({
  value,
  onChange,
  domain,
  step,
  leftLabel,
  rightLabel,
  ariaLabel,
}: Props) {
  const [domainMin, domainMax] = domain;
  const span = domainMax - domainMin;
  const trackRef = useRef<HTMLDivElement | null>(null);
  const draggingRef = useRef<"min" | "max" | null>(null);
  const [focused, setFocused] = useState<"min" | "max" | null>(null);
  const uid = useId();

  const pctOf = (v: number) => ((v - domainMin) / span) * 100;
  const leftPct = pctOf(value.min);
  const rightPct = pctOf(value.max);

  const valueFromPointer = useCallback(
    (clientX: number) => {
      const el = trackRef.current;
      if (!el) return domainMin;
      const rect = el.getBoundingClientRect();
      const frac = clamp((clientX - rect.left) / rect.width, 0, 1);
      return snap(domainMin + frac * span, step, domainMin);
    },
    [domainMin, span, step],
  );

  const beginDrag = (handle: "min" | "max", clientX: number) => {
    draggingRef.current = handle;
    moveTo(handle, valueFromPointer(clientX));
  };

  const moveTo = useCallback(
    (handle: "min" | "max", raw: number) => {
      const v = clamp(raw, domainMin, domainMax);
      if (handle === "min") {
        onChange({ min: Math.min(v, value.max), max: value.max });
      } else {
        onChange({ min: value.min, max: Math.max(v, value.min) });
      }
    },
    [domainMin, domainMax, onChange, value.min, value.max],
  );

  useEffect(() => {
    function onMove(e: PointerEvent) {
      if (!draggingRef.current) return;
      moveTo(draggingRef.current, valueFromPointer(e.clientX));
    }
    function onUp() {
      draggingRef.current = null;
    }
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    };
  }, [moveTo, valueFromPointer]);

  const onTrackPointerDown = (e: React.PointerEvent) => {
    if (e.target !== e.currentTarget) return;
    const raw = valueFromPointer(e.clientX);
    // Move whichever handle is nearer.
    const nearMin = Math.abs(raw - value.min) <= Math.abs(raw - value.max);
    beginDrag(nearMin ? "min" : "max", e.clientX);
  };

  const onHandlePointerDown =
    (handle: "min" | "max") => (e: React.PointerEvent) => {
      e.stopPropagation();
      (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
      beginDrag(handle, e.clientX);
    };

  const onHandleKeyDown =
    (handle: "min" | "max") => (e: React.KeyboardEvent) => {
      const current = handle === "min" ? value.min : value.max;
      let next = current;
      if (e.key === "ArrowLeft" || e.key === "ArrowDown") next = current - step;
      else if (e.key === "ArrowRight" || e.key === "ArrowUp")
        next = current + step;
      else if (e.key === "Home") next = domainMin;
      else if (e.key === "End") next = domainMax;
      else if (e.key === "PageDown") next = current - step * 5;
      else if (e.key === "PageUp") next = current + step * 5;
      else return;
      e.preventDefault();
      moveTo(handle, snap(next, step, domainMin));
    };

  const HANDLE = 14;
  const handleStyle = (left: string, focus: boolean): React.CSSProperties => ({
    left,
    width: HANDLE,
    height: HANDLE,
    backgroundColor: "#c55a3f",
    border: "2px solid #faf7f2",
    boxShadow: "0 1px 2px rgba(0,0,0,0.15)",
    outline: focus ? "2px solid #c55a3f" : "2px solid transparent",
    outlineOffset: 2,
    cursor: "grab",
    touchAction: "none",
  });

  return (
    <div>
      <div
        role="group"
        aria-label={ariaLabel}
        className="relative mx-1 h-5 select-none"
      >
        <div
          ref={trackRef}
          onPointerDown={onTrackPointerDown}
          className="absolute left-0 right-0 top-1/2 h-[4px] -translate-y-1/2 cursor-pointer rounded-full"
          style={{ backgroundColor: "#eadbc3" }}
        >
          <div
            className="absolute top-0 h-full rounded-full bg-accent-medium"
            style={{ left: `${leftPct}%`, right: `${100 - rightPct}%` }}
          />
        </div>

        <button
          type="button"
          role="slider"
          aria-valuemin={domainMin}
          aria-valuemax={domainMax}
          aria-valuenow={value.min}
          aria-valuetext={`${leftLabel} edge: ${formatSigned(value.min)}`}
          onPointerDown={onHandlePointerDown("min")}
          onKeyDown={onHandleKeyDown("min")}
          onFocus={() => setFocused("min")}
          onBlur={() => setFocused(null)}
          className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={handleStyle(`${leftPct}%`, focused === "min")}
          aria-describedby={`${uid}-readout`}
        />

        <button
          type="button"
          role="slider"
          aria-valuemin={domainMin}
          aria-valuemax={domainMax}
          aria-valuenow={value.max}
          aria-valuetext={`${rightLabel} edge: ${formatSigned(value.max)}`}
          onPointerDown={onHandlePointerDown("max")}
          onKeyDown={onHandleKeyDown("max")}
          onFocus={() => setFocused("max")}
          onBlur={() => setFocused(null)}
          className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={handleStyle(`${rightPct}%`, focused === "max")}
          aria-describedby={`${uid}-readout`}
        />
      </div>

      <div
        id={`${uid}-readout`}
        className="mt-[2px] flex items-center justify-between px-1 text-[10px] text-muted-soft"
        style={{ fontVariantNumeric: "tabular-nums" }}
      >
        <span>{formatSigned(value.min)}</span>
        <span className="text-muted-soft/70">
          {leftLabel} &middot; {rightLabel}
        </span>
        <span>{formatSigned(value.max)}</span>
      </div>
    </div>
  );
}
