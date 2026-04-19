// Shared warm terracotta density scale. Both the map fills and the
// themes-panel bars use the same ramp so "big region" and "big theme"
// read as the same visual signal.
export const DENSITY_COLORS = [
  "#f3e7d4", // light sand
  "#ecd1ae",
  "#e0b383",
  "#d28f5d",
  "#b5533a", // deep terracotta
] as const;

export const DENSITY_BAR_BG = "#efe6d6"; // unfilled bar track

// Perceptual fraction for a count, scaled by sqrt against a dynamic max.
// sqrt keeps small counts visible and avoids the largest count swamping
// everything on a linear scale.
export function densityFraction(count: number, maxCount: number): number {
  if (maxCount <= 0 || count <= 0) return 0;
  return Math.sqrt(count) / Math.sqrt(maxCount);
}

export function densityColor(fraction: number): string {
  if (fraction <= 0) return DENSITY_COLORS[0];
  const idx = Math.min(
    DENSITY_COLORS.length - 1,
    Math.floor(fraction * DENSITY_COLORS.length),
  );
  return DENSITY_COLORS[idx];
}
