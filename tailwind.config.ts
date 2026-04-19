import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#faf7f2",
        card: "#f6f0e4",
        ink: "#1a1714",
        "ink-strong": "#2a2520",
        muted: "#6b645c",
        "muted-soft": "#8a8377",
        line: "#d9d2c4",
        "line-soft": "#ece3d0",
        // Tiered accent — loud for the headline surface (selected region),
        // medium for secondary emphasis (theme bars, slider fill), subtle
        // and quiet for hover tints and soft fills.
        "accent-loud": "#c55a3f",
        "accent-medium": "#b85f42",
        "accent-subtle": "#d8a292",
        "accent-quiet": "#f0d5c8",
        // Legacy aliases kept for components that still reference them.
        accent: "#b85f42",
        "accent-dark": "#8a3d2a",
      },
      fontFamily: {
        serif: ["Lora", "Source Serif Pro", "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
