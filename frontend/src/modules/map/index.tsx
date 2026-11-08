// MapView: the interactive portfolio map (docs/prd/modules/map.md). Default export, mounted by App.tsx.
import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl, {
  type GeoJSONSource,
  type Map as MLMap,
  type MapLayerMouseEvent,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Home, Minus, Plus } from "lucide-react";
import {
  useBuildings,
  useDemoState,
  useImpact,
  useOverlays,
  useScenarios,
  useUtilities,
} from "../../shared/queries";
import { useUIStore } from "../../shared/ui-store";
import { money, riskColor, type RiskLevel } from "../../shared/format";
import { offlineStyle } from "./offline";
import {
  BASEMAP_URL,
  FALLBACK_STYLE,
  LAYERS,
  SOURCES,
  TOGGLES,
  empty,
} from "./style";
import TimelineControl from "./TimelineControl";
import Legend from "./Legend";
import "./map.css";

type FC = { type: "FeatureCollection"; features: unknown[] };

export default function MapView() {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const markers = useRef(new Map<string, maplibregl.Marker>());
  const [basemap, setBasemap] = useState("local");
  const [moving, setMoving] = useState(false);
  const [ready, setReady] = useState(0); // bumps every time a style (basemap or fallback) has our layers
  const { selectedBuildingId, selectBuilding, layers } = useUIStore();
  const selectRef = useRef(selectBuilding);
  selectRef.current = selectBuilding;

  const state = useDemoState();
  const scenarios = useScenarios();
  const buildings = useBuildings();
  const impacts = useImpact();
  const utilities = useUtilities();
  const overlays = useOverlays(state.data?.step_hour);
  const city = scenarios.data?.find(
    (s) => s.id === state.data?.scenario_id,
  )?.city;

  // ---------- create the map once ----------
  useEffect(() => {
    if (!container.current) return;
    const map = new maplibregl.Map({
      container: container.current,
      style: offlineStyle,
      center: [-95.4, 29.76],
      zoom: 9.6,
      attributionControl: { compact: true },
    });
    mapRef.current = map;
    map.on("movestart", () => setMoving(true));
    map.on("moveend", () => setMoving(false));
    const addOurLayers = () => {
      for (const id of SOURCES)
        if (!map.getSource(id))
          map.addSource(id, { type: "geojson", data: empty() });
      const glyphs = Boolean(map.getStyle().glyphs);
      for (const layer of LAYERS)
        if (!map.getLayer(layer.id) && (glyphs || layer.type !== "symbol"))
          map.addLayer(layer);
      setReady((n) => n + 1);
    };
    map.on("style.load", addOurLayers);
    const controller = new AbortController();
    const fallback = window.setTimeout(() => controller.abort(), 3500);
    fetch(BASEMAP_URL, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Basemap unavailable");
        return response.json();
      })
      .then((style) => {
        if (!controller.signal.aborted) {
          map.setStyle(style);
          setBasemap("remote");
        }
      })
      .catch(() => {});
    map.on("error", () => {
      if (
        map.getStyle()?.sources &&
        Object.keys(map.getStyle().sources).some(
          (id) =>
            !SOURCES.includes(id as (typeof SOURCES)[number]) &&
            id !== "context",
        )
      ) {
        map.setStyle(offlineStyle);
        setBasemap("local");
      }
    });
    map.on("click", "buildings", (e: MapLayerMouseEvent) => {
      const id = e.features?.[0]?.properties?.id;
      if (id) selectRef.current(String(id));
    });
    const popup = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 14,
      className: "storm-popup",
    });
    const hover = (e: MapLayerMouseEvent) => {
      const p = e.features?.[0]?.properties as
        | Record<string, string>
        | undefined;
      if (!p) return;
      map.getCanvas().style.cursor = "pointer";
      popup.setLngLat(e.lngLat).setDOMContent(tooltip(p)).addTo(map);
    };
    const leave = () => {
      map.getCanvas().style.cursor = "";
      popup.remove();
    };
    map.on("mousemove", "buildings", hover);
    map.on("mouseleave", "buildings", leave);
    map.on("mousemove", "power", hover);
    map.on("mouseleave", "power", leave);
    return () => {
      window.clearTimeout(fallback);
      controller.abort();
      for (const marker of markers.current.values()) marker.remove();
      markers.current.clear();
      popup.remove();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // ---------- data -> sources (setData only when the data changes) ----------
  const buildingFC = useMemo<FC>(() => {
    const list = buildings.data ?? [];
    const byId = new Map((impacts.data ?? []).map((i) => [i.building_id, i]));
    const roots = list.map((b) => Math.sqrt(b.replacement_value_cents));
    const lo = Math.min(...roots),
      hi = Math.max(...roots);
    return {
      type: "FeatureCollection",
      features: list.map((b, k) => {
        const i = byId.get(b.id);
        const risk = i?.risk as RiskLevel | undefined;
        const net = i?.money.net_exposure_cents;
        return {
          type: "Feature",
          geometry: { type: "Point", coordinates: [b.lon, b.lat] },
          properties: {
            id: b.id,
            name: b.name,
            risk: risk ?? "unknown",
            color: riskColor(risk ?? "none"),
            r: 8 + (hi > lo ? (14 * (roots[k] - lo)) / (hi - lo) : 7),
            label: `${b.name} · ${net == null ? "impact unavailable" : money(net)}`,
            net: net == null ? "impact unavailable" : money(net),
            driver: i?.drivers?.[0] ?? "",
            selected: b.id === selectedBuildingId,
            approved: Boolean(i?.with_approved_actions),
            kind: "building",
          },
        };
      }),
    };
  }, [buildings.data, impacts.data, selectedBuildingId]);

  const powerFC = useMemo<FC>(
    () => ({
      type: "FeatureCollection",
      features: (utilities.data ?? []).map((u) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [u.lon, u.lat] },
        properties: {
          id: u.id,
          name: u.name,
          down: u.down,
          kind: "power",
          driver: u.down ? "Down now" : "Up",
        },
      })),
    }),
    [utilities.data],
  );

  const linkFC = useMemo<FC>(() => {
    const b = buildings.data?.find((x) => x.id === selectedBuildingId);
    const u = b && utilities.data?.find((x) => x.id === b.utility_node_id);
    return {
      type: "FeatureCollection",
      features:
        b && u
          ? [
              {
                type: "Feature",
                properties: {},
                geometry: {
                  type: "LineString",
                  coordinates: [
                    [b.lon, b.lat],
                    [u.lon, u.lat],
                  ],
                },
              },
            ]
          : [],
    };
  }, [buildings.data, utilities.data, selectedBuildingId]);

  useEffect(() => {
    setData(mapRef.current, "buildings", buildingFC);
  }, [buildingFC, ready]);
  useEffect(() => {
    setData(mapRef.current, "power", powerFC);
  }, [powerFC, ready]);
  useEffect(() => {
    setData(mapRef.current, "link", linkFC);
  }, [linkFC, ready]);
  useEffect(() => {
    if (overlays.data) setData(mapRef.current, "hazard", overlays.data as FC);
  }, [overlays.data, ready]);

  // ---------- layer toggles from the panel ----------
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    for (const [toggle, ids] of Object.entries(TOGGLES)) {
      const on = layers[toggle as keyof typeof layers] !== false;
      for (const id of ids)
        if (map.getLayer(id))
          map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
    }
  }, [layers, ready]);

  // Accessible square markers keep labels usable without remote glyph/font services.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const active = new Set<string>();
    for (const feature of buildingFC.features as any[]) {
      const p = feature.properties;
      active.add(p.id);
      let marker = markers.current.get(p.id);
      if (!marker) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "storm-building-button";
        button.addEventListener("click", () => selectRef.current(p.id));
        button.addEventListener("focus", () => {
          const coords = feature.geometry.coordinates;
          map.easeTo({ center: coords, duration: 200 });
        });
        marker = new maplibregl.Marker({ element: button, anchor: "center" })
          .setLngLat(feature.geometry.coordinates)
          .addTo(map);
        markers.current.set(p.id, marker);
      }
      const button = marker.getElement() as HTMLButtonElement;
      button.setAttribute(
        "aria-label",
        `${p.name} · ${p.net} · ${p.risk} risk`,
      );
      button.setAttribute("aria-pressed", String(p.selected));
      button.dataset.buildingId = p.id;
      button.dataset.risk = p.risk;
      button.dataset.approved = String(p.approved);
      button.style.display = layers.buildings === false ? "none" : "";
      button.classList.toggle("is-selected", p.selected);
      button.classList.toggle("is-approved", p.approved);
      button.replaceChildren();
      const square = document.createElement("span");
      square.className = "storm-building-square";
      square.style.backgroundColor = p.color;
      square.style.width = square.style.height = `${p.r * 1.4}px`;
      if (p.approved) square.textContent = "✓";
      const label = document.createElement("span");
      label.className = "storm-building-label";
      label.textContent = p.label;
      button.title = p.driver || p.label;
      button.append(square, label);
    }
    for (const [id, marker] of markers.current)
      if (!active.has(id)) {
        marker.remove();
        markers.current.delete(id);
      }
    for (const id of ["buildings", "buildings-approved", "buildings-label"])
      if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", "none");
  }, [buildingFC, ready, layers.buildings]);

  // ---------- fly to the scenario's buildings when the scenario changes ----------
  const framed = useRef<string | null>(null);
  const frame = () => {
    const map = mapRef.current;
    const pts = (buildings.data ?? [])
      .filter((b) => b.city === city)
      .map((b) => [b.lon, b.lat] as [number, number]);
    if (!map || !pts.length) return;
    const bounds = pts.reduce(
      (bb, p) => bb.extend(p),
      new maplibregl.LngLatBounds(pts[0], pts[0]),
    );
    map.fitBounds(bounds, {
      padding: { top: 90, bottom: 90, left: 150, right: 90 },
      maxZoom: 11.5,
      duration: 1200,
    });
  };
  useEffect(() => {
    const key = state.data?.scenario_id;
    if (!ready || !key || !city || !buildings.data || framed.current === key)
      return;
    framed.current = key;
    frame();
  });

  useEffect(() => {
    if (!ready || !selectedBuildingId) return;
    const b = buildings.data?.find((b) => b.id === selectedBuildingId);
    if (b)
      mapRef.current?.easeTo({
        center: [b.lon, b.lat],
        zoom: Math.max(mapRef.current.getZoom(), 11),
        duration: 350,
      });
  }, [selectedBuildingId, ready, buildings.data]);

  // ---------- one animation loop: water pulses; impact water "rises" when the step changes ----------
  const phase = state.data?.phase;
  const riseStart = useRef(0);
  useEffect(() => {
    riseStart.current = performance.now();
  }, [state.data?.step_hour]);
  useEffect(() => {
    if (
      window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
      (!layers.hazard && !layers.power)
    )
      return;
    let raf = 0;
    const tick = (t: number) => {
      const map = mapRef.current;
      if (map?.getLayer("water-fill")) {
        const rise =
          phase === "forecast" ? 1 : Math.min(1, (t - riseStart.current) / 800);
        const pulse = 0.85 + 0.15 * Math.sin(t / 900);
        map.setPaintProperty("water-fill", "fill-opacity", [
          "case",
          ["==", ["get", "forecast"], true],
          0.16 * pulse,
          0.3 * pulse * rise,
        ]);
        map.setPaintProperty("power", "circle-opacity", [
          "case",
          ["get", "down"],
          0.55 + 0.45 * Math.abs(Math.sin(t / 400)),
          1,
        ]);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [phase, ready, layers.hazard, layers.power]);

  return (
    <div
      className="storm-map"
      data-map-ready={ready > 0}
      data-map-moving={moving}
      data-basemap={basemap}
    >
      <div
        ref={container}
        className="storm-map-canvas"
        aria-label="Portfolio map"
        role="region"
      />
      <TimelineControl />
      <div className="storm-map-tools">
        <button
          type="button"
          aria-label="Fit the scenario"
          title="Fit the scenario"
          onClick={frame}
        >
          <Home size={16} />
        </button>
        <button
          type="button"
          aria-label="Zoom in"
          title="Zoom in"
          onClick={() => mapRef.current?.zoomIn()}
        >
          <Plus size={16} />
        </button>
        <button
          type="button"
          aria-label="Zoom out"
          title="Zoom out"
          onClick={() => mapRef.current?.zoomOut()}
        >
          <Minus size={16} />
        </button>
      </div>
      <Legend />
      <div className="storm-local-note">
        {basemap === "local"
          ? "Local backdrop · approximate roads/coast"
          : "© OpenFreeMap · © OpenStreetMap contributors"}
      </div>
    </div>
  );
}

function setData(map: MLMap | null, id: string, data: FC) {
  const source = map?.getSource(id) as GeoJSONSource | undefined;
  source?.setData(data as Parameters<GeoJSONSource["setData"]>[0]);
}

/** Hover card built with DOM nodes (no HTML strings: names come from data). */
function tooltip(p: Record<string, string>): HTMLElement {
  const root = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = p.name;
  root.append(title);
  const line = (text: string) => {
    const d = document.createElement("div");
    d.textContent = text;
    root.append(d);
  };
  if (p.kind === "building") {
    line(`${p.risk} risk · net ${p.net}`);
    if (p.driver) line(p.driver);
  } else {
    line(`Substation · ${p.driver}`);
  }
  return root;
}
