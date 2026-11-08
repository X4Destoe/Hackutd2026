import { useEffect, useMemo, useRef, useState, type RefObject } from "react";
import type { MapRef } from "react-map-gl/maplibre";
import { ChevronDown, ChevronUp, Home, Layers, Minus, Plus, Box } from "lucide-react";
import { phaseColor, riskColor, type RiskLevel } from "../../shared/format";
import { useDemoState, useSetHour, useTimeline } from "../../shared/queries";
import { useUIStore, type Layer } from "../../shared/ui-store";
import { useMapOverlays } from "./data";
import { groupOverlays, viewFor } from "./geo";

const RISK: RiskLevel[] = ["none", "low", "moderate", "high", "severe"];
const LAYER_ORDER: Layer[] = ["hazard", "buildings", "power", "help", "workorders", "messages"];
const LAYER_LABEL: Record<Layer, string> = {
  hazard: "Hazard overlay",
  buildings: "Buildings by $ at risk",
  power: "Power grid",
  help: "Help sites and residents",
  workorders: "Work orders",
  messages: "Messages",
};

export function stepLabel(hour: number) {
  const abs = Math.abs(hour);
  const body = abs >= 72 && abs % 24 === 0 ? `${abs / 24}d` : `${abs}h`;
  if (hour < 0) return `−${body}`;
  if (hour > 0) return `+${body}`;
  return body;
}

function hazardRamp(groups: Record<string, unknown[]>) {
  if (groups.flood_water?.length) return { name: "Flood", from: "#d6ecff", to: "#143e6b" };
  if (groups.surge_water?.length) return { name: "Surge", from: "#b7e3ea", to: "#0e3d4a" };
  if (groups.snow_ice?.length) return { name: "Ice", from: "#ffffff", to: "#8eabc8" };
  if (groups.wind_swirl?.length) return { name: "Wind", from: "#f8fafc", to: "#64748b" };
  if (groups.fire_smoke?.length) return { name: "Fire", from: "#ffedd5", to: "#c2410c" };
  if (groups.forecast_cone?.length) return { name: "Forecast", from: "#f5f3ff", to: "#7c3aed" };
  return { name: "Hazard", from: "#e2e8f0", to: "#64748b" };
}

export function TimelineControl() {
  const timeline = useTimeline();
  const demo = useDemoState();
  const setHour = useSetHour();
  const steps = timeline.data ?? [];
  const hour = demo.data?.step_hour;
  const stepsRef = useRef(steps);
  const hourRef = useRef(hour);
  stepsRef.current = steps;
  hourRef.current = hour;

  const go = (delta: number) => {
    const list = stepsRef.current;
    if (!list.length || setHour.isPending) return;
    const index = list.findIndex((step) => step.hour === hourRef.current);
    const next = list[Math.min(list.length - 1, Math.max(0, (index < 0 ? 0 : index) + delta))];
    if (next && next.hour !== hourRef.current) setHour.mutate(next.hour);
  };

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const tag = (event.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
        event.preventDefault();
        go(-1);
      } else if (event.key === "ArrowRight" || event.key === "ArrowDown") {
        event.preventDefault();
        go(1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setHour]);

  const index = steps.findIndex((step) => step.hour === hour);
  const current = index >= 0 ? steps[index] : undefined;
  return (
    <nav className="timeline" aria-label="Scenario timeline">
      <button type="button" className="time-arrow" aria-label="Earlier step" disabled={index <= 0} onClick={() => go(-1)}>
        <ChevronUp size={16} />
      </button>
      <div className="time-steps" aria-busy={setHour.isPending}>
        {steps.map((step) => (
          <button
            key={step.hour}
            type="button"
            className="time-step"
            style={{ borderLeftColor: phaseColor(step.phase) }}
            aria-pressed={step.hour === hour}
            aria-label={`${stepLabel(step.hour)}, ${step.phase}`}
            title={step.narrative}
            onClick={() => setHour.mutate(step.hour)}
          >
            {stepLabel(step.hour)}
          </button>
        ))}
      </div>
      <button type="button" className="time-arrow" aria-label="Later step" disabled={index < 0 || index >= steps.length - 1} onClick={() => go(1)}>
        <ChevronDown size={16} />
      </button>
      <p className="sr-only" aria-live="polite">{current ? `${stepLabel(current.hour)}, ${current.phase}. ${current.narrative}` : ""}</p>
    </nav>
  );
}

export function MapTools({ mapRef }: { mapRef: RefObject<MapRef | null> }) {
  const demo = useDemoState();
  const { layers, toggleLayer, setAllLayers } = useUIStore();
  const [open, setOpen] = useState(false);
  const [pitched, setPitched] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (!wrap.current?.contains(event.target as Node)) setOpen(false);
    };
    window.addEventListener("mousedown", close);
    return () => window.removeEventListener("mousedown", close);
  }, [open]);

  const flyHome = () => {
    const view = viewFor(demo.data?.scenario_id);
    mapRef.current?.flyTo({ center: [view.longitude, view.latitude], zoom: view.zoom, pitch: 0, bearing: 0, duration: 800, essential: true });
    setPitched(false);
  };
  const tilt = () => {
    const next = pitched ? 0 : 50;
    mapRef.current?.easeTo({ pitch: next, duration: 500 });
    setPitched(next > 0);
  };

  return (
    <div className="map-tools" ref={wrap}>
      <button type="button" aria-label="Fly to the scenario" onClick={flyHome}><Home size={16} /></button>
      <button type="button" aria-label="Map layers" aria-expanded={open} onClick={() => setOpen((value) => !value)}><Layers size={16} /></button>
      {open && (
        <div className="layer-pop" role="group" aria-label="Map layers">
          <div className="layer-pop-actions">
            <button type="button" onClick={() => setAllLayers(true)}>Select all</button>
            <button type="button" onClick={() => setAllLayers(false)}>Clear</button>
          </div>
          {LAYER_ORDER.map((layer) => (
            <button key={layer} type="button" aria-pressed={layers[layer]} onClick={() => toggleLayer(layer)}>
              <span className={`check${layers[layer] ? " on" : ""}`} />
              {LAYER_LABEL[layer]}
            </button>
          ))}
        </div>
      )}
      <button type="button" aria-label="Zoom in" onClick={() => mapRef.current?.zoomIn({ duration: 200 })}><Plus size={16} /></button>
      <button type="button" aria-label="Zoom out" onClick={() => mapRef.current?.zoomOut({ duration: 200 })}><Minus size={16} /></button>
      <button type="button" aria-label="Tilt the map" aria-pressed={pitched} onClick={tilt}><Box size={16} /></button>
    </div>
  );
}

export function Legend({ hour }: { hour?: number }) {
  const overlays = useMapOverlays(hour);
  const groups = useMemo(() => groupOverlays(overlays.data), [overlays.data]);
  const ramp = hazardRamp(groups);
  return (
    <aside className="legend" aria-label="Map legend">
      <strong>Net exposure</strong>
      <ul>
        {RISK.map((level) => (
          <li key={level}><span className="swatch" style={{ background: riskColor(level) }} />{level}</li>
        ))}
      </ul>
      <strong>{ramp.name}</strong>
      <span className="ramp" style={{ background: `linear-gradient(90deg, ${ramp.from}, ${ramp.to})` }} />
    </aside>
  );
}

export function Disclaimer() {
  return <p className="disclaimer">Footprints approximate · illustrative</p>;
}
