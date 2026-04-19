"use client";

import { useEffect, useRef } from "react";
import maplibregl, { type MapGeoJSONFeature } from "maplibre-gl";
import type { OblastFeatureCollection, Region } from "@/lib/types";
import {
  DENSITY_COLORS,
  densityColor,
  densityFraction,
} from "@/lib/density-scale";

type Props = {
  regions: Region[];
  geojson: OblastFeatureCollection | null;
  selectedRegion: string | null;
  onSelectRegion: (region: string) => void;
  // When a theme filter is active, counts for the *current* visible set.
  // Regions absent from the map (Donbas etc.) aren't in here.
  regionCountOverrides: Map<string, number> | null;
};

const FILL_SCALE = DENSITY_COLORS;

function scaleColor(count: number, max: number) {
  return densityColor(densityFraction(count, max));
}

export function RegionMap({
  regions,
  geojson,
  selectedRegion,
  onSelectRegion,
  regionCountOverrides,
}: Props) {
  const container = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const onSelectRef = useRef(onSelectRegion);
  onSelectRef.current = onSelectRegion;
  const overridesRef = useRef(regionCountOverrides);
  overridesRef.current = regionCountOverrides;

  useEffect(() => {
    if (!container.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: container.current,
      style: {
        version: 8,
        sources: {},
        layers: [
          {
            id: "paper-bg",
            type: "background",
            paint: { "background-color": "#faf7f2" },
          },
        ],
      },
      center: [31.5, 48.8],
      zoom: 4.6,
      minZoom: 3.8,
      maxZoom: 8,
      attributionControl: false,
      dragRotate: false,
      pitchWithRotate: false,
    });
    map.touchZoomRotate.disableRotation();
    mapRef.current = map;

    map.on("load", () => {
      // Oblast fills
      if (geojson) {
        // Attach song_count to each feature for data-driven fill
        const max = Math.max(...regions.map((r) => r.song_count), 1);
        const counts = new Map(regions.map((r) => [r.region, r.song_count]));
        const enriched: OblastFeatureCollection = {
          type: "FeatureCollection",
          features: geojson.features.map((f) => ({
            ...f,
            properties: {
              ...f.properties,
              song_count: counts.get(f.properties.region) ?? 0,
              fill: scaleColor(counts.get(f.properties.region) ?? 0, max),
            } as typeof f.properties & { song_count: number; fill: string },
          })),
        };

        map.addSource("oblasts", { type: "geojson", data: enriched });

        map.addLayer({
          id: "oblast-fill",
          type: "fill",
          source: "oblasts",
          paint: {
            "fill-color": [
              "case",
              ["boolean", ["feature-state", "selected"], false],
              "#c55a3f", // accent-loud on select
              ["get", "fill"],
            ],
            "fill-opacity": [
              "case",
              ["boolean", ["feature-state", "selected"], false],
              1.0,
              ["boolean", ["feature-state", "hover"], false],
              0.9,
              0.7,
            ],
          },
        });
        // MapLibre style-spec supports per-property `-transition` but the
        // TS types don't expose it; apply via setPaintProperty with a cast.
        (map as unknown as { setPaintProperty: (id: string, k: string, v: unknown) => void }).setPaintProperty(
          "oblast-fill",
          "fill-color-transition",
          { duration: 200, delay: 0 },
        );
        (map as unknown as { setPaintProperty: (id: string, k: string, v: unknown) => void }).setPaintProperty(
          "oblast-fill",
          "fill-opacity-transition",
          { duration: 200, delay: 0 },
        );

        map.addLayer({
          id: "oblast-line",
          type: "line",
          source: "oblasts",
          paint: {
            "line-color": [
              "case",
              ["boolean", ["feature-state", "selected"], false],
              "#1a1714",
              "#8a8377",
            ],
            "line-width": [
              "case",
              ["boolean", ["feature-state", "selected"], false],
              1.6,
              0.6,
            ],
            "line-opacity": [
              "case",
              ["boolean", ["feature-state", "selected"], false],
              1.0,
              0.55,
            ],
          },
        });

        // Centroid labels rendered as DOM markers (no external glyphs
        // endpoint required). We tag each marker with the region name so
        // the select-effect effect can flip its "is-selected" class.
        for (const r of regions) {
          const el = document.createElement("div");
          el.className = "oblast-label";
          el.textContent = r.region;
          el.dataset.region = r.region;
          new maplibregl.Marker({ element: el, anchor: "center" })
            .setLngLat(r.centroid)
            .addTo(map);
        }
      } else {
        // Fallback: circles at centroids. Only triggers if geojson download failed.
        const max = Math.max(...regions.map((r) => r.song_count), 1);
        const fc = {
          type: "FeatureCollection" as const,
          features: regions.map((r) => ({
            type: "Feature" as const,
            properties: {
              region: r.region,
              song_count: r.song_count,
              fill: scaleColor(r.song_count, max),
            },
            geometry: {
              type: "Point" as const,
              coordinates: r.centroid,
            },
          })),
        };
        map.addSource("oblasts", { type: "geojson", data: fc });
        map.addLayer({
          id: "oblast-fill",
          type: "circle",
          source: "oblasts",
          paint: {
            "circle-radius": [
              "interpolate",
              ["linear"],
              ["get", "song_count"],
              0,
              6,
              max,
              30,
            ],
            "circle-color": ["get", "fill"],
            "circle-stroke-color": "#1a1714",
            "circle-stroke-width": 0.6,
          },
        });
      }

      // Hover state + tooltip
      let hoveredId: string | number | null = null;
      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        offset: 8,
      });

      const source = "oblasts";
      const mainLayer = geojson ? "oblast-fill" : "oblast-fill";

      const setHover = (
        feature: MapGeoJSONFeature | null,
      ) => {
        if (hoveredId !== null) {
          map.setFeatureState(
            { source, id: hoveredId },
            { hover: false },
          );
        }
        if (feature && feature.id !== undefined) {
          hoveredId = feature.id;
          map.setFeatureState(
            { source, id: feature.id },
            { hover: true },
          );
        } else {
          hoveredId = null;
        }
      };

      map.on("mousemove", mainLayer, (e) => {
        const f = e.features?.[0];
        if (!f) return;
        map.getCanvas().style.cursor = "pointer";
        setHover(f);
        const p = f.properties as {
          region: string;
          song_count: number;
        };
        const region = regions.find((r) => r.region === p.region);
        const singers = region?.singer_count ?? 0;
        popup
          .setLngLat(e.lngLat)
          .setHTML(
            `<strong>${p.region}</strong> — ${p.song_count.toLocaleString()} song${p.song_count === 1 ? "" : "s"}, ${singers} singer${singers === 1 ? "" : "s"}`,
          )
          .addTo(map);
      });
      map.on("mouseleave", mainLayer, () => {
        map.getCanvas().style.cursor = "";
        setHover(null);
        popup.remove();
      });
      map.on("click", mainLayer, (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties as { region: string };
        onSelectRef.current(p.region);
      });

      // Assign stable feature IDs so feature-state works.
      // (MapLibre needs them; we patch them in by re-setting source data.)
      if (geojson) {
        const src = map.getSource("oblasts") as maplibregl.GeoJSONSource;
        const data = {
          type: "FeatureCollection" as const,
          features: (geojson.features as Array<
            GeoJSON.Feature & { properties: { region: string; song_count?: number; fill?: string } }
          >).map((f, i) => {
            const max = Math.max(...regions.map((r) => r.song_count), 1);
            const counts = new Map(regions.map((r) => [r.region, r.song_count]));
            const c = counts.get((f.properties as { region: string }).region) ?? 0;
            return {
              ...f,
              id: i,
              properties: {
                ...f.properties,
                song_count: c,
                fill: scaleColor(c, max),
              },
            };
          }),
        };
        src.setData(data);
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Recolor the oblast fills when the theme filter changes.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !geojson) return;
    const apply = () => {
      const src = map.getSource("oblasts") as
        | maplibregl.GeoJSONSource
        | undefined;
      if (!src) return;
      const useOverrides = regionCountOverrides;
      const counts = new Map<string, number>();
      for (const r of regions) {
        counts.set(
          r.region,
          useOverrides?.get(r.region) ?? r.song_count,
        );
      }
      const max = Math.max(...counts.values(), 1);
      const data = {
        type: "FeatureCollection" as const,
        features: geojson.features.map((f, i) => {
          const region = f.properties.region;
          const c = counts.get(region) ?? 0;
          return {
            ...f,
            id: i,
            properties: {
              ...f.properties,
              song_count: c,
              fill: scaleColor(c, max),
            },
          };
        }),
      };
      src.setData(data);
    };
    if (map.isStyleLoaded()) apply();
    else map.once("load", apply);
  }, [regionCountOverrides, regions, geojson]);

  // Update selected-feature state when selectedRegion changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const src = map.getSource("oblasts") as
        | maplibregl.GeoJSONSource
        | undefined;
      if (!src) return;
      // Clear all selected states
      for (let i = 0; i < (geojson?.features.length ?? regions.length); i++) {
        map.setFeatureState(
          { source: "oblasts", id: i },
          { selected: false },
        );
      }
      // Clear any prior label highlight, then apply the new one.
      const labelEls = map
        .getContainer()
        .querySelectorAll<HTMLElement>(".oblast-label");
      labelEls.forEach((el) => el.classList.remove("is-selected"));
      if (!selectedRegion || !geojson) return;
      const idx = geojson.features.findIndex(
        (f) => f.properties.region === selectedRegion,
      );
      if (idx >= 0) {
        map.setFeatureState(
          { source: "oblasts", id: idx },
          { selected: true },
        );
        labelEls.forEach((el) => {
          if (el.dataset.region === selectedRegion) {
            el.classList.add("is-selected");
          }
        });
        const region = regions.find((r) => r.region === selectedRegion);
        if (region) {
          map.flyTo({
            center: region.centroid,
            zoom: Math.max(map.getZoom(), 5.4),
            duration: 600,
          });
        }
      }
    };
    if (map.isStyleLoaded()) apply();
    else map.once("load", apply);
  }, [selectedRegion, geojson, regions]);

  return <div ref={container} className="h-full w-full" />;
}
