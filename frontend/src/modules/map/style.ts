/// <reference types="vite/client" />
// Map layers and paint (docs/prd/modules/map.md, 04-ui-spec §5). All data comes from the API; this file only draws it.
import type {
  ExpressionSpecification,
  LayerSpecification,
  StyleSpecification,
} from "maplibre-gl";

export const BASEMAP_URL =
  (import.meta.env.VITE_MAP_STYLE as string | undefined) ||
  "https://tiles.openfreemap.org/styles/liberty";
export const LABEL_FONT = ["Noto Sans Regular"];

/** Used when the basemap cannot load (venue Wi-Fi down): plain background, our layers still draw. */
export const FALLBACK_STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [
    { id: "bg", type: "background", paint: { "background-color": "#eef1ec" } },
  ],
};

export const SOURCES = ["hazard", "power", "link", "buildings"] as const;
export const empty = () => ({
  type: "FeatureCollection" as const,
  features: [],
});

// water depth (ft) -> color: light to deep blue; storm surge darker
const water = (
  light: string,
  mid: string,
  deep: string,
  deepest: string,
): ExpressionSpecification => [
  "step",
  ["to-number", ["get", "intensity"], 0],
  light,
  1,
  mid,
  3,
  deep,
  6,
  deepest,
];
const isForecast: ExpressionSpecification = ["==", ["get", "forecast"], true];

export const LAYERS: LayerSpecification[] = [
  {
    id: "wind-fill",
    type: "fill",
    source: "hazard",
    filter: [
      "all",
      ["==", ["get", "style"], "wind_swirl"],
      ["==", ["geometry-type"], "Polygon"],
    ],
    paint: { "fill-color": "#7d93ad", "fill-opacity": 0.05 },
  },
  {
    id: "wind-edge",
    type: "line",
    source: "hazard",
    filter: ["==", ["get", "style"], "wind_swirl"],
    paint: {
      "line-color": "#7d93ad",
      "line-opacity": 0.35,
      "line-width": 1,
      "line-dasharray": [4, 3],
    },
  },
  {
    id: "snow-fill",
    type: "fill",
    source: "hazard",
    filter: ["==", ["get", "style"], "snow_ice"],
    paint: {
      "fill-color": ["case", isForecast, "#c9d8f2", "#bcd6f2"],
      "fill-opacity": ["case", isForecast, 0.25, 0.5],
    },
  },
  {
    id: "snow-edge",
    type: "line",
    source: "hazard",
    filter: ["==", ["get", "style"], "snow_ice"],
    paint: {
      "line-color": ["case", isForecast, "#7c3aed", "#8fb8e0"],
      "line-width": 2,
      "line-dasharray": [3, 2],
    },
  },
  {
    id: "water-fill",
    type: "fill",
    source: "hazard",
    filter: [
      "all",
      ["in", ["get", "style"], ["literal", ["flood_water", "surge_water"]]],
      ["==", ["geometry-type"], "Polygon"],
    ],
    paint: {
      "fill-color": [
        "case",
        isForecast,
        "#81c5e5",
        ["==", ["get", "style"], "surge_water"],
        water("#5b8fd1", "#2f6bb5", "#174f91", "#0b3666"),
        water("#8ec5f2", "#4b9be6", "#1f6fc4", "#0d4a94"),
      ],
      "fill-opacity": ["case", isForecast, 0.16, 0.3],
    },
  },
  {
    id: "water-contours",
    type: "line",
    source: "hazard",
    filter: [
      "all",
      ["!=", ["get", "forecast"], true],
      ["in", ["get", "style"], ["literal", ["flood_water", "surge_water"]]],
    ],
    paint: { "line-color": "#277ca8", "line-width": 0.8, "line-opacity": 0.22 },
  },
  {
    id: "water-edge",
    type: "line",
    source: "hazard",
    filter: [
      "all",
      isForecast,
      ["in", ["get", "style"], ["literal", ["flood_water", "surge_water"]]],
    ],
    paint: {
      "line-color": "#7c3aed",
      "line-width": 1.5,
      "line-opacity": 0.6,
      "line-dasharray": [2, 2],
    },
  },
  {
    id: "track",
    type: "line",
    source: "hazard",
    filter: [
      "all",
      ["==", ["get", "style"], "forecast_cone"],
      ["==", ["geometry-type"], "LineString"],
    ],
    layout: { "line-cap": "round" },
    paint: {
      "line-color": "#7c3aed",
      "line-width": 3,
      "line-dasharray": [2, 2],
    },
  },
  {
    id: "link",
    type: "line",
    source: "link",
    paint: {
      "line-color": "#b7791f",
      "line-width": 2,
      "line-dasharray": [2, 1.5],
    },
  },
  {
    id: "power",
    type: "circle",
    source: "power",
    paint: {
      "circle-radius": 6,
      "circle-color": ["case", ["get", "down"], "#dc2626", "#4b5c55"],
      "circle-stroke-color": "#fff",
      "circle-stroke-width": 2,
    },
  },
  {
    id: "buildings-approved",
    type: "circle",
    source: "buildings",
    filter: ["==", ["get", "approved"], true],
    paint: {
      "circle-radius": ["+", ["get", "r"], 6],
      "circle-color": "rgba(0,0,0,0)",
      "circle-stroke-color": "#16834a",
      "circle-stroke-width": 3,
    },
  },
  {
    id: "buildings",
    type: "circle",
    source: "buildings",
    paint: {
      "circle-radius": ["get", "r"],
      "circle-color": ["get", "color"],
      "circle-opacity": 0.92,
      "circle-stroke-color": [
        "case",
        ["get", "selected"],
        "#10261b",
        "#ffffff",
      ],
      "circle-stroke-width": ["case", ["get", "selected"], 4, 2],
    },
  },
  {
    id: "buildings-label",
    type: "symbol",
    source: "buildings",
    minzoom: 9.5,
    layout: {
      "text-field": ["get", "label"],
      "text-font": LABEL_FONT,
      "text-size": 12,
      "text-anchor": "top",
      "text-offset": [0, 1.3],
      "text-max-width": 14,
      "text-allow-overlap": false,
    },
    paint: {
      "text-color": "#20342b",
      "text-halo-color": "#ffffff",
      "text-halo-width": 1.6,
    },
  },
];

/** Which map layers each panel layer toggle controls. */
export const TOGGLES: Record<string, string[]> = {
  hazard: [
    "wind-fill",
    "wind-edge",
    "snow-fill",
    "snow-edge",
    "water-fill",
    "water-edge",
    "water-contours",
    "track",
  ],
  power: ["power", "link"],
  buildings: ["buildings", "buildings-approved", "buildings-label"],
};
