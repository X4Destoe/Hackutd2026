import { useEffect, useMemo, useRef, type RefObject } from "react";
import { Layer, Source, type MapRef } from "react-map-gl/maplibre";
import type { Map as MapLibreMap } from "maplibre-gl";
import { useMapOverlays } from "./data";
import { bindFrame } from "./frame";
import { bbox, collection, groupOverlays, type StormFeature } from "./geo";

const floodPaint = {
  "fill-color": ["interpolate", ["linear"], ["coalesce", ["to-number", ["get", "intensity"]], 0], 0, "#d6ecff", 1, "#7eb6e6", 3, "#2f6fad", 6, "#143e6b"],
  "fill-opacity": 0.45,
};
const surgePaint = {
  "fill-color": ["interpolate", ["linear"], ["coalesce", ["to-number", ["get", "intensity"]], 0], 0, "#b7e3ea", 1, "#3d8f9c", 3, "#145e68", 6, "#0e3d4a"],
  "fill-opacity": 0.42,
};
const surgeLinePaint = { "line-color": "#08343c", "line-width": 2, "line-dasharray": [1, 2, 3, 2], "line-opacity": 0.8 };
const snowPaint = {
  "fill-color": "#8fb4d6",
  "fill-opacity": ["interpolate", ["linear"], ["coalesce", ["to-number", ["get", "intensity"]], 0], 0, 0.34, 1, 0.45],
};
const snowLinePaint = { "line-color": "#5d7c9c", "line-width": 1.5, "line-opacity": 0.85 };
const windPaint = {
  "fill-color": "#64748b",
  "fill-opacity": 0.18,
};
const windLinePaint = { "line-color": "#475569", "line-width": 1.2, "line-opacity": 0.45 };
const conePaint = { "fill-color": "#7c3aed", "fill-opacity": 0.1 };
const coneLinePaint = { "line-color": "#7c3aed", "line-width": 2, "line-dasharray": [2, 2] };
const firePaint = {
  "fill-color": ["interpolate", ["linear"], ["coalesce", ["to-number", ["get", "intensity"]], 0], 0, "#ffedd5", 1, "#f97316", 3, "#c2410c"],
  "fill-opacity": 0.4,
};

const FLAKES = 280;

type Flake = { x: number; y: number; s: number; v: number; phase: number };
let flakes: Flake[] = [];

function drawSnow(canvas: HTMLCanvasElement | null, map: MapLibreMap, features: StormFeature[] | undefined, now: number) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (width < 2 || height < 2) return;
  const pxW = Math.floor(width * dpr);
  const pxH = Math.floor(height * dpr);
  if (canvas.width !== pxW || canvas.height !== pxH) {
    canvas.width = pxW;
    canvas.height = pxH;
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  const box = bbox(features);
  if (!box || !features?.length) return;
  const sw = map.project([box[0], box[1]]);
  const ne = map.project([box[2], box[3]]);
  const left = Math.max(0, Math.min(sw.x, ne.x));
  const right = Math.min(width, Math.max(sw.x, ne.x));
  const top = Math.max(0, Math.min(sw.y, ne.y));
  const bottom = Math.min(height, Math.max(sw.y, ne.y));
  const rectW = right - left;
  const rectH = bottom - top;
  if (rectW < 4 || rectH < 4) return;
  if (flakes.length !== FLAKES || flakes[0].v < 2) {
    flakes = Array.from({ length: FLAKES }, () => ({
      x: Math.random(),
      y: Math.random(),
      s: 3.4 + Math.random() * 3.2,
      v: 2.4 + Math.random() * 2.2,
      phase: Math.random() * Math.PI * 2,
    }));
  }
  for (const flake of flakes) {
    flake.y += flake.v / rectH;
    flake.x += Math.sin(now / 700 + flake.phase) * 0.6 / rectW;
    if (flake.y > 1) flake.y -= 1;
    if (flake.x < 0) flake.x += 1;
    if (flake.x > 1) flake.x -= 1;
    const x = left + flake.x * rectW;
    const y = top + flake.y * rectH;
    ctx.fillStyle = "#3e5c78";
    ctx.fillRect(x, y, flake.s + 1.6, flake.s + 1.6);
    ctx.fillStyle = "#f7fbff";
    ctx.fillRect(x, y, flake.s, flake.s);
  }
}

export default function HazardLayers({
  hour,
  mapRef,
  snowCanvas,
}: {
  hour?: number;
  mapRef: RefObject<MapRef | null>;
  snowCanvas: RefObject<HTMLCanvasElement | null>;
}) {
  const overlays = useMapOverlays(hour);
  const groups = useMemo(() => groupOverlays(overlays.data), [overlays.data]);
  const born = useRef<number | null>(null);
  const seenHour = useRef(hour);
  const dashOk = useRef(true);
  const groupsRef = useRef(groups);
  groupsRef.current = groups;

  useEffect(() => {
    if (seenHour.current !== hour) {
      seenHour.current = hour;
      born.current = performance.now();
    }
  }, [hour]);

  useEffect(() => {
    const tick = (now: number) => {
      const map = mapRef.current?.getMap();
      if (!map) return;
      const age = born.current == null ? 1 : Math.min(1, (now - born.current) / 800);
      if (!map.isStyleLoaded()) {
        drawSnow(snowCanvas.current, map, groupsRef.current.snow_ice, now);
        return;
      }
      const pulse = 0.45 + 0.1 * Math.sin((now / 2500) * Math.PI * 2);
      if (map.getLayer("flood-fill")) map.setPaintProperty("flood-fill", "fill-opacity", pulse * age);
      if (map.getLayer("surge-fill")) {
        const surge = 0.4 + 0.1 * Math.sin((now / 2200) * Math.PI * 2);
        map.setPaintProperty("surge-fill", "fill-opacity", surge * age);
      }
      if (dashOk.current && map.getLayer("surge-line")) {
        const shift = (now / 140) % 4;
        const lead = Math.max(0.05, shift);
        try {
          map.setPaintProperty("surge-line", "line-dasharray", [lead, 2, Math.max(0.05, 4 - shift), 2]);
        } catch {
          dashOk.current = false;
        }
      }
      if (map.getLayer("wind-fill")) {
        map.setPaintProperty("wind-fill", "fill-opacity", 0.1 + 0.16 * (0.5 + 0.5 * Math.sin(now / 700)));
      }
      drawSnow(snowCanvas.current, map, groupsRef.current.snow_ice, now);
    };
    return bindFrame(tick);
  }, [mapRef, snowCanvas]);

  useEffect(() => () => {
    const canvas = snowCanvas.current;
    const ctx = canvas?.getContext("2d");
    if (canvas && ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
  }, [snowCanvas]);

  return (
    <>
      <Source id="flood" type="geojson" data={collection(groups.flood_water)}>
        <Layer id="flood-fill" type="fill" paint={floodPaint as never} />
      </Source>
      <Source id="surge" type="geojson" data={collection(groups.surge_water)}>
        <Layer id="surge-fill" type="fill" paint={surgePaint as never} />
        <Layer id="surge-line" type="line" paint={surgeLinePaint as never} />
      </Source>
      <Source id="snow" type="geojson" data={collection(groups.snow_ice)}>
        <Layer id="snow-fill" type="fill" paint={snowPaint as never} />
        <Layer id="snow-line" type="line" paint={snowLinePaint as never} />
      </Source>
      <Source id="wind" type="geojson" data={collection(groups.wind_swirl)}>
        <Layer id="wind-fill" type="fill" paint={windPaint as never} />
        <Layer id="wind-line" type="line" paint={windLinePaint as never} />
      </Source>
      <Source id="cone" type="geojson" data={collection(groups.forecast_cone)}>
        <Layer id="cone-fill" type="fill" paint={conePaint as never} />
        <Layer id="cone-line" type="line" paint={coneLinePaint as never} />
      </Source>
      <Source id="fire" type="geojson" data={collection(groups.fire_smoke)}>
        <Layer id="fire-fill" type="fill" paint={firePaint as never} />
      </Source>
    </>
  );
}
