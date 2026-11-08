// Help sites on the map: a pin per type, a capacity ring, a red X when unsafe,
// and a short arc when a resident is routed. The referral record has distance
// but not a coordinate, so the arc starts distance_mi away on a stable bearing.
import { useEffect, useRef } from "react";
import maplibregl, { type Map as MLMap } from "maplibre-gl";
import type { Model } from "../../shared/api";
import { useReferrals, useResources } from "../../shared/queries";
import { useUIStore } from "../../shared/ui-store";

type Resource = Model<"Resource">;
type Referral = Model<"Referral">;
type Arc = { from: [number, number]; to: [number, number]; born: number };

const TYPE_LABEL: Record<Resource["type"], string> = {
  shelter: "Shelter",
  warming_center: "Warming center",
  claim_site: "Claims adjuster",
  hotel: "Hotel",
  repair_vendor: "Repair crew",
  cbre_help_site: "CBRE help site",
};
const RING: Record<Resource["status"], string> = {
  open: "#16834a",
  full: "#eab308",
  unsafe: "#dc2626",
  closed: "#94a3b8",
};
const ARC_MS = 4200;

function hash(value: string): number {
  let h = 0;
  for (let i = 0; i < value.length; i++) h = (h * 33 + value.charCodeAt(i)) >>> 0;
  return h;
}

function origin(site: Resource, miles: number, partyId: string): [number, number] {
  const bearing = ((hash(partyId) % 360) * Math.PI) / 180;
  const distance = Math.max(miles, 0.35);
  const dLat = (distance / 69) * Math.cos(bearing);
  const dLon = (distance / (69 * Math.cos((site.lat * Math.PI) / 180))) * Math.sin(bearing);
  return [site.lon + dLon, site.lat + dLat];
}

function svgEl(name: string, attrs: Record<string, string>): SVGElement {
  const el = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  return el;
}

function typeMark(type: Resource["type"]): SVGSVGElement {
  const svg = svgEl("svg", { viewBox: "0 0 16 16", class: "help-pin-icon", "aria-hidden": "true" }) as SVGSVGElement;
  const stroke = { fill: "none", stroke: "currentColor", "stroke-width": "1.6", "stroke-linejoin": "miter" };
  if (type === "shelter" || type === "cbre_help_site") {
    svg.append(svgEl("path", { ...stroke, d: "M2 7.5 8 2.5 14 7.5 V14 H2 Z" }));
    if (type === "cbre_help_site") svg.append(svgEl("path", { ...stroke, d: "M6.5 14 V9.5 H9.5 V14" }));
  } else if (type === "warming_center") {
    svg.append(svgEl("circle", { ...stroke, cx: "8", cy: "8", r: "2.4" }));
    svg.append(svgEl("path", { ...stroke, d: "M8 2.2 V4.2 M8 11.8 V13.8 M2.2 8 H4.2 M11.8 8 H13.8" }));
  } else if (type === "claim_site") {
    svg.append(svgEl("path", { ...stroke, d: "M8 1.8 13.2 4 V8.2 C13.2 11.2 10.8 13.4 8 14.2 5.2 13.4 2.8 11.2 2.8 8.2 V4 Z" }));
  } else if (type === "hotel") {
    svg.append(svgEl("rect", { ...stroke, x: "3", y: "3", width: "10", height: "10" }));
    svg.append(svgEl("path", { ...stroke, d: "M6.2 13 V9.2 H9.8 V13" }));
  } else {
    svg.append(svgEl("path", { ...stroke, d: "M3 11.5 6.2 8.3 8.2 10.3 11.5 7 M10.2 7 H12.4 V9.2" }));
  }
  return svg;
}

function pinButton(site: Resource, onOpen: () => void): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `help-pin help-pin-${site.status} help-type-${site.type}`;
  button.dataset.helpId = site.id;
  button.dataset.helpType = site.type;
  button.dataset.helpStatus = site.status;
  const free = Math.max(0, site.capacity - site.used);
  const label = `${site.name}. ${TYPE_LABEL[site.type]}. ${site.status}. ${free} of ${site.capacity} places left. Open Help Sites`;
  button.title = label;
  button.setAttribute("aria-label", label);
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    onOpen();
  });

  const ring = svgEl("svg", { viewBox: "0 0 36 36", class: "help-pin-ring", "aria-hidden": "true" }) as SVGSVGElement;
  const radius = 15;
  const length = 2 * Math.PI * radius;
  const used = site.capacity > 0 ? Math.min(1, site.used / site.capacity) : 1;
  ring.append(svgEl("circle", { cx: "18", cy: "18", r: String(radius), class: "help-pin-track" }));
  ring.append(
    svgEl("circle", {
      cx: "18",
      cy: "18",
      r: String(radius),
      class: "help-pin-used",
      stroke: RING[site.status],
      "stroke-dasharray": `${used * length} ${length}`,
    }),
  );
  const plate = document.createElement("span");
  plate.className = "help-pin-plate";
  plate.append(typeMark(site.type));
  const name = document.createElement("span");
  name.className = "help-pin-label";
  name.textContent = site.status === "unsafe" ? `${TYPE_LABEL[site.type]} · unsafe` : TYPE_LABEL[site.type];
  button.append(ring, plate);
  if (site.status === "unsafe") {
    const mark = document.createElement("span");
    mark.className = "help-pin-x";
    mark.textContent = "×";
    mark.setAttribute("aria-hidden", "true");
    button.append(mark);
  }
  button.append(name);
  return button;
}

export default function HelpLayer({ map, city }: { map: MLMap | null; city?: string }) {
  const sites = useResources(city);
  const referrals = useReferrals();
  const { layers, setPanelView } = useUIStore();
  const openHelp = useRef(setPanelView);
  openHelp.current = setPanelView;
  const sitesRef = useRef<Resource[]>([]);
  sitesRef.current = sites.data ?? [];
  const pushArc = useRef<(referral: Referral) => void>(() => {});
  const seen = useRef<Map<string, string> | null>(null);

  useEffect(() => {
    if (!map || layers.help === false) return;
    const markers: maplibregl.Marker[] = [];
    for (const site of sitesRef.current) {
      if (city && site.city !== city) continue;
      const button = pinButton(site, () => openHelp.current("help"));
      markers.push(new maplibregl.Marker({ element: button, anchor: "center" }).setLngLat([site.lon, site.lat]).addTo(map));
    }
    return () => markers.forEach((marker) => marker.remove());
  }, [map, city, layers.help, sites.data]);

  useEffect(() => {
    if (!map || layers.help === false) return;
    const canvas = document.createElement("canvas");
    canvas.className = "help-arc-canvas";
    canvas.dataset.referralArcs = "true";
    map.getContainer().appendChild(canvas);
    const arcs: Arc[] = [];
    let frame = 0;
    let running = false;
    const resize = () => {
      const box = map.getContainer().getBoundingClientRect();
      const ratio = Math.min(2, window.devicePixelRatio || 1);
      canvas.width = Math.max(1, Math.round(box.width * ratio));
      canvas.height = Math.max(1, Math.round(box.height * ratio));
      canvas.style.width = `${box.width}px`;
      canvas.style.height = `${box.height}px`;
    };
    const paint = (now: number) => {
      resize();
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(canvas.width / map.getContainer().clientWidth, 0, 0, canvas.height / map.getContainer().clientHeight, 0, 0);
      ctx.clearRect(0, 0, map.getContainer().clientWidth, map.getContainer().clientHeight);
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      for (let i = arcs.length - 1; i >= 0; i--) {
        const arc = arcs[i];
        const age = now - arc.born;
        if (age > ARC_MS) {
          arcs.splice(i, 1);
          continue;
        }
        const t = reduce ? 1 : Math.min(1, age / (ARC_MS * 0.72));
        const fade = age > ARC_MS * 0.72 ? 1 - (age - ARC_MS * 0.72) / (ARC_MS * 0.28) : 1;
        const a = map.project(arc.from);
        const b = map.project(arc.to);
        const midX = (a.x + b.x) / 2 + (a.y - b.y) * 0.18;
        const midY = (a.y + b.y) / 2 + (b.x - a.x) * 0.18;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        const c1x = a.x + (midX - a.x) * t;
        const c1y = a.y + (midY - a.y) * t;
        const endX = a.x + (b.x - a.x) * t;
        const endY = a.y + (b.y - a.y) * t;
        ctx.quadraticCurveTo(c1x, c1y, endX, endY);
        ctx.lineCap = "butt";
        ctx.strokeStyle = `rgba(255,255,255,${0.9 * fade})`;
        ctx.lineWidth = 5;
        ctx.stroke();
        ctx.strokeStyle = `rgba(31,122,69,${fade})`;
        ctx.lineWidth = 2.5;
        ctx.stroke();
      }
      canvas.dataset.arcCount = String(arcs.length);
      if (arcs.length) frame = requestAnimationFrame(paint);
      else running = false;
    };
    const kick = () => {
      if (running) return;
      running = true;
      frame = requestAnimationFrame(paint);
    };
    pushArc.current = (referral) => {
      const site = sitesRef.current.find((item) => item.id === referral.resource_id);
      if (!site || (city && site.city !== city)) return;
      arcs.push({ from: origin(site, referral.distance_mi ?? 1, referral.party_id), to: [site.lon, site.lat], born: performance.now() });
      kick();
    };
    map.on("move", kick);
    return () => {
      cancelAnimationFrame(frame);
      map.off("move", kick);
      pushArc.current = () => {};
      canvas.remove();
    };
  }, [map, city, layers.help]);

  useEffect(() => {
    if (!referrals.data || layers.help === false) return;
    if (seen.current === null) {
      seen.current = new Map(referrals.data.map((referral) => [referral.id, referral.status]));
      return;
    }
    for (const referral of referrals.data) {
      const previous = seen.current.get(referral.id);
      const placed = referral.status === "routed" || referral.status === "rerouted";
      if (placed && referral.resource_id && previous !== referral.status) pushArc.current(referral);
      seen.current.set(referral.id, referral.status);
    }
  }, [referrals.data, layers.help, map]);

  const visible = layers.help === false ? 0 : (sites.data ?? []).filter((site) => !city || site.city === city).length;
  return <span className="help-pin-count" data-help-pins={visible} />;
}
