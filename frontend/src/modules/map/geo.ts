import type { Feature, FeatureCollection, Geometry, Position } from "geojson";
import type { StyleSpecification } from "maplibre-gl";
import type { GeoJSONCollection } from "../../shared/api";

export type StormFeature = Feature<Geometry, { style?: string; intensity?: number; hazard?: string }>;

const meta = import.meta as unknown as { env?: { VITE_MAP_STYLE?: string } };

/** OpenFreeMap Liberty. Override with VITE_MAP_STYLE. */
export const MAP_STYLE = meta.env?.VITE_MAP_STYLE || "https://tiles.openfreemap.org/styles/liberty";

export const SCENARIO_VIEWS: Record<string, { longitude: number; latitude: number; zoom: number }> = {
  harvey_houston: { longitude: -95.47, latitude: 29.75, zoom: 10.3 },
  uri_dallas: { longitude: -96.82, latitude: 32.84, zoom: 10.4 },
  ian_fort_myers: { longitude: -81.88, latitude: 26.55, zoom: 10.2 },
};

export function viewFor(scenarioId?: string) {
  return (scenarioId && SCENARIO_VIEWS[scenarioId]) || SCENARIO_VIEWS.harvey_houston;
}

export function groupOverlays(data: GeoJSONCollection | undefined) {
  const groups: Record<string, StormFeature[]> = {};
  for (const feature of data?.features ?? []) {
    const style = String(feature.properties?.style ?? "");
    (groups[style] ??= []).push(feature as unknown as StormFeature);
  }
  return groups;
}

export const EMPTY: FeatureCollection = { type: "FeatureCollection", features: [] };

export function collection(features: StormFeature[] | undefined): FeatureCollection {
  if (!features?.length) return EMPTY;
  return { type: "FeatureCollection", features };
}

export function bbox(features: StormFeature[] | undefined): [number, number, number, number] | null {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  const walk = (coords: unknown) => {
    if (!Array.isArray(coords)) return;
    if (typeof coords[0] === "number" && typeof coords[1] === "number") {
      const [x, y] = coords as Position;
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
      return;
    }
    coords.forEach(walk);
  };
  for (const feature of features ?? []) {
    const geometry = feature.geometry as { coordinates?: unknown } | null;
    walk(geometry?.coordinates);
  }
  if (!Number.isFinite(minX)) return null;
  return [minX, minY, maxX, maxY];
}

const OFFLINE: FeatureCollection = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { kind: "water" },
      geometry: {
        type: "Polygon",
        coordinates: [[
          [-97.6, 25.8], [-97.2, 27.6], [-95.4, 28.9], [-94.0, 29.6], [-90.8, 29.2],
          [-89.2, 29.1], [-88.4, 30.2], [-84.5, 29.6], [-82.6, 27.4], [-81.7, 25.4],
          [-83.2, 24.4], [-90.0, 24.0], [-97.6, 24.2], [-97.6, 25.8],
        ]],
      },
    },
    {
      type: "Feature",
      properties: { kind: "road" },
      geometry: { type: "LineString", coordinates: [[-95.9, 29.76], [-94.0, 29.7], [-90.2, 30.0], [-84.3, 30.4]] },
    },
    {
      type: "Feature",
      properties: { kind: "road" },
      geometry: { type: "LineString", coordinates: [[-95.37, 29.76], [-95.4, 31.0], [-96.8, 32.78]] },
    },
    {
      type: "Feature",
      properties: { kind: "road" },
      geometry: { type: "LineString", coordinates: [[-81.87, 26.5], [-81.9, 27.4], [-82.45, 28.4]] },
    },
  ],
};

/** Approximate Gulf and highways when the vector style cannot be fetched. */
export const OFFLINE_STYLE: StyleSpecification = {
  version: 8,
  name: "offline-backdrop",
  sources: { backdrop: { type: "geojson", data: OFFLINE } },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": "#d7e4ea" } },
    { id: "gulf", type: "fill", source: "backdrop", filter: ["==", ["get", "kind"], "water"], paint: { "fill-color": "#9ec3d6" } },
    { id: "roads", type: "line", source: "backdrop", filter: ["==", ["get", "kind"], "road"], paint: { "line-color": "#c4bba8", "line-width": 1.6 } },
  ],
};
