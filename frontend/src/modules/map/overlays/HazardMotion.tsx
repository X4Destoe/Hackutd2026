import { useEffect } from "react";
import type { Map as MLMap } from "maplibre-gl";

type Feature = { properties?: Record<string, unknown>; geometry?: { type: string; coordinates: unknown } };
type Collection = { features: unknown[] };
const STYLES = new Set(["snow_ice", "surge_water", "wind_swirl"]);

/** Decorative motion clipped to API geometry. MapView owns the only animation clock. */
export default function HazardMotion({ map, data, enabled }: { map: MLMap | null; data?: Collection; enabled: boolean }) {
  useEffect(() => {
    if (!map || !enabled || !data) return;
    const canvas = document.createElement("canvas");
    canvas.className = "storm-hazard-motion";
    canvas.setAttribute("aria-hidden", "true");
    Object.assign(canvas.style, { position: "absolute", inset: "0", pointerEvents: "none", zIndex: "0", width: "100%", height: "100%" });
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    map.getContainer().appendChild(canvas);
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    type Shape = { path: Path2D; left: number; top: number; right: number; bottom: number; forecast: boolean };
    const shapes = new Map<string, Shape>();
    let width = 0, height = 0, ratio = 1;
    const rebuild = () => {
      width = map.getContainer().clientWidth;
      height = map.getContainer().clientHeight;
      ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      shapes.clear();
      for (const raw of data.features) {
        const feature = raw as Feature;
        const style = String(feature.properties?.style ?? "");
        const geometry = feature.geometry;
        if (!STYLES.has(style) || !geometry || !["Polygon", "MultiPolygon"].includes(geometry.type)) continue;
        const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
        const shape = shapes.get(style) ?? { path: new Path2D(), left: width, top: height, right: 0, bottom: 0, forecast: true };
        shape.forecast &&= feature.properties?.forecast === true;
        for (const polygon of polygons as number[][][][]) for (const ring of polygon) {
          ring.forEach((point, index) => {
            const projected = map.project([point[0], point[1]]);
            if (index === 0) shape.path.moveTo(projected.x, projected.y);
            else shape.path.lineTo(projected.x, projected.y);
            shape.left = Math.min(shape.left, projected.x); shape.right = Math.max(shape.right, projected.x);
            shape.top = Math.min(shape.top, projected.y); shape.bottom = Math.max(shape.bottom, projected.y);
          });
          shape.path.closePath();
        }
        shapes.set(style, shape);
      }
      canvas.dataset.motionStyles = [...shapes.keys()].sort().join(",");
    };
    const paint = () => {
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.clearRect(0, 0, width, height);
      canvas.dataset.reducedMotion = String(reduced.matches);
      if (document.hidden || reduced.matches || !width || !height) return;
      const time = performance.now() / 1000;
      let drawn = 0;
      const budget = Math.floor(300 / Math.max(1, shapes.size));
      for (const [style, shape] of shapes) {
        const left = Math.max(0, shape.left), top = Math.max(0, shape.top);
        const w = Math.min(width, shape.right) - left, h = Math.min(height, shape.bottom) - top;
        if (w <= 0 || h <= 0) continue;
        ctx.save(); ctx.clip(shape.path);
        ctx.globalAlpha = shape.forecast ? 0.35 : 0.65;
        const count = Math.min(budget, style === "snow_ice" ? 240 : 80);
        for (let i = 0; i < count; i++) {
          const seedX = ((i * 0.61803398875) % 1), seedY = ((i * 0.41421356237) % 1);
          if (style === "snow_ice") {
            const x = left + ((seedX * w + Math.sin(time * 0.7 + i) * 12 + w) % w);
            const y = top + ((seedY * h + time * (14 + i % 17)) % h);
            ctx.beginPath(); ctx.arc(x, y, 1 + i % 3 * 0.45, 0, Math.PI * 2);
            ctx.fillStyle = "#ffffff"; ctx.fill();
            ctx.strokeStyle = "#7d9ebc"; ctx.lineWidth = 0.4; ctx.stroke();
          } else if (style === "surge_water") {
            const x = left + seedX * w, y = top + ((seedY * h + time * 8) % h);
            ctx.beginPath(); ctx.moveTo(x - 8, y);
            ctx.quadraticCurveTo(x, y - 3 - Math.sin(time * 2 + i) * 2, x + 8, y);
            ctx.strokeStyle = shape.forecast ? "#617cbd" : "#d4f2ff"; ctx.lineWidth = 1.2; ctx.stroke();
          } else {
            const angle = seedX * Math.PI * 2 + time * 0.18;
            const radius = 0.12 + seedY * 0.8;
            const x = left + w / 2 + Math.cos(angle) * w * radius / 2;
            const y = top + h / 2 + Math.sin(angle) * h * radius / 2;
            ctx.beginPath(); ctx.moveTo(x, y);
            ctx.lineTo(x - Math.sin(angle) * 12, y + Math.cos(angle) * 7);
            ctx.strokeStyle = "#607b96"; ctx.lineWidth = 1; ctx.stroke();
          }
          drawn++;
        }
        ctx.restore();
      }
      canvas.dataset.particleCount = String(drawn);
      canvas.dataset.frame = String(Math.floor(time * 30));
    };
    const refresh = () => { rebuild(); paint(); };
    refresh();
    map.on("render", paint); map.on("move", rebuild); map.on("resize", refresh);
    reduced.addEventListener("change", paint);
    return () => {
      map.off("render", paint); map.off("move", rebuild); map.off("resize", refresh);
      reduced.removeEventListener("change", paint); canvas.remove();
    };
  }, [map, data, enabled]);
  return null;
}
