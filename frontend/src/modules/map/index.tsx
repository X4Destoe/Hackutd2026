// MapView: the interactive portfolio map (docs/prd/modules/map.md). Default export, mounted by App.tsx.
import { useEffect, useMemo, useRef, useState } from 'react';
import maplibregl, { type GeoJSONSource, type Map as MLMap, type MapLayerMouseEvent } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Home, Minus, Plus } from 'lucide-react';
import { useBuildings, useDemoState, useImpact, useOverlays, useScenarios, useUtilities } from '../../shared/queries';
import { useUIStore } from '../../shared/ui-store';
import { money, riskColor, type RiskLevel } from '../../shared/format';
import { BASEMAP_URL, FALLBACK_STYLE, LAYERS, SOURCES, TOGGLES, empty } from './style';
import TimelineControl from './TimelineControl';
import Legend from './Legend';
import './map.css';

type FC = { type: 'FeatureCollection'; features: unknown[] };

export default function MapView() {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
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
  const city = scenarios.data?.find((s) => s.id === state.data?.scenario_id)?.city;

  // ---------- create the map once ----------
  useEffect(() => {
    if (!container.current) return;
    const map = new maplibregl.Map({ container: container.current, style: BASEMAP_URL, center: [-95.4, 29.76], zoom: 9.6,
      attributionControl: { compact: true } });
    mapRef.current = map;
    let loaded = false;
    const addOurLayers = () => {
      loaded = true;
      for (const id of SOURCES) if (!map.getSource(id)) map.addSource(id, { type: 'geojson', data: empty() });
      const glyphs = Boolean(map.getStyle().glyphs);
      for (const layer of LAYERS) if (!map.getLayer(layer.id) && (glyphs || layer.type !== 'symbol')) map.addLayer(layer);
      setReady((n) => n + 1);
    };
    map.on('style.load', addOurLayers);
    const fallback = window.setTimeout(() => { if (!loaded) { console.warn('Basemap unreachable; using plain background'); map.setStyle(FALLBACK_STYLE); } }, 5000);
    map.on('click', 'buildings', (e: MapLayerMouseEvent) => { const id = e.features?.[0]?.properties?.id; if (id) selectRef.current(String(id)); });
    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 14, className: 'storm-popup' });
    const hover = (e: MapLayerMouseEvent) => {
      const p = e.features?.[0]?.properties as Record<string, string> | undefined;
      if (!p) return;
      map.getCanvas().style.cursor = 'pointer';
      popup.setLngLat(e.lngLat).setDOMContent(tooltip(p)).addTo(map);
    };
    const leave = () => { map.getCanvas().style.cursor = ''; popup.remove(); };
    map.on('mousemove', 'buildings', hover);
    map.on('mouseleave', 'buildings', leave);
    map.on('mousemove', 'power', hover);
    map.on('mouseleave', 'power', leave);
    return () => { window.clearTimeout(fallback); popup.remove(); map.remove(); mapRef.current = null; };
  }, []);

  // ---------- data -> sources (setData only when the data changes) ----------
  const buildingFC = useMemo<FC>(() => {
    const list = buildings.data ?? [];
    const byId = new Map((impacts.data ?? []).map((i) => [i.building_id, i]));
    const roots = list.map((b) => Math.sqrt(b.replacement_value_cents));
    const lo = Math.min(...roots), hi = Math.max(...roots);
    return { type: 'FeatureCollection', features: list.map((b, k) => {
      const i = byId.get(b.id);
      const risk = (i?.risk ?? 'none') as RiskLevel;
      const net = i?.money.net_exposure_cents ?? 0;
      return { type: 'Feature', geometry: { type: 'Point', coordinates: [b.lon, b.lat] }, properties: {
        id: b.id, name: b.name, risk, color: riskColor(risk), r: 8 + (hi > lo ? (14 * (roots[k] - lo)) / (hi - lo) : 7),
        label: `${b.name} · ${net > 0 ? money(net) : 'safe'}`, net: net > 0 ? money(net) : '$0', driver: i?.drivers?.[0] ?? '',
        selected: b.id === selectedBuildingId, approved: Boolean(i?.with_approved_actions), kind: 'building' } };
    }) };
  }, [buildings.data, impacts.data, selectedBuildingId]);

  const powerFC = useMemo<FC>(() => ({ type: 'FeatureCollection', features: (utilities.data ?? []).map((u) => ({
    type: 'Feature', geometry: { type: 'Point', coordinates: [u.lon, u.lat] },
    properties: { id: u.id, name: u.name, down: u.down, kind: 'power', driver: u.down ? 'Down now' : 'Up' } })) }), [utilities.data]);

  const linkFC = useMemo<FC>(() => {
    const b = buildings.data?.find((x) => x.id === selectedBuildingId);
    const u = b && utilities.data?.find((x) => x.id === b.utility_node_id);
    return { type: 'FeatureCollection', features: b && u ? [{ type: 'Feature', properties: {},
      geometry: { type: 'LineString', coordinates: [[b.lon, b.lat], [u.lon, u.lat]] } }] : [] };
  }, [buildings.data, utilities.data, selectedBuildingId]);

  useEffect(() => { setData(mapRef.current, 'buildings', buildingFC); }, [buildingFC, ready]);
  useEffect(() => { setData(mapRef.current, 'power', powerFC); }, [powerFC, ready]);
  useEffect(() => { setData(mapRef.current, 'link', linkFC); }, [linkFC, ready]);
  useEffect(() => { if (overlays.data) setData(mapRef.current, 'hazard', overlays.data as FC); }, [overlays.data, ready]);

  // ---------- layer toggles from the panel ----------
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    for (const [toggle, ids] of Object.entries(TOGGLES)) {
      const on = layers[toggle as keyof typeof layers] !== false;
      for (const id of ids) if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none');
    }
  }, [layers, ready]);

  // ---------- fly to the scenario's buildings when the scenario changes ----------
  const framed = useRef<string | null>(null);
  const frame = () => {
    const map = mapRef.current;
    const pts = (buildings.data ?? []).filter((b) => b.city === city).map((b) => [b.lon, b.lat] as [number, number]);
    if (!map || !pts.length) return;
    const bounds = pts.reduce((bb, p) => bb.extend(p), new maplibregl.LngLatBounds(pts[0], pts[0]));
    map.fitBounds(bounds, { padding: { top: 90, bottom: 90, left: 150, right: 90 }, maxZoom: 11.5, duration: 1200 });
  };
  useEffect(() => {
    const key = state.data?.scenario_id;
    if (!ready || !key || !city || !buildings.data || framed.current === key) return;
    framed.current = key;
    frame();
  });

  // ---------- one animation loop: water pulses; impact water "rises" when the step changes ----------
  const phase = state.data?.phase;
  const riseStart = useRef(0);
  useEffect(() => { riseStart.current = performance.now(); }, [state.data?.step_hour]);
  useEffect(() => {
    let raf = 0;
    const tick = (t: number) => {
      const map = mapRef.current;
      if (map?.getLayer('water-fill')) {
        const rise = phase === 'forecast' ? 1 : Math.min(1, (t - riseStart.current) / 800);
        const pulse = 0.85 + 0.15 * Math.sin(t / 900);
        map.setPaintProperty('water-fill', 'fill-opacity', ['case', ['==', ['get', 'forecast'], true], 0.16 * pulse, 0.3 * pulse * rise]);
        map.setPaintProperty('power', 'circle-opacity', ['case', ['get', 'down'], 0.55 + 0.45 * Math.abs(Math.sin(t / 400)), 1]);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [phase, ready]);

  return (
    <div className="storm-map">
      <div ref={container} className="storm-map-canvas" aria-label="Portfolio map" role="region" />
      <TimelineControl />
      <div className="storm-map-tools">
        <button type="button" aria-label="Fit the scenario" title="Fit the scenario" onClick={frame}><Home size={16} /></button>
        <button type="button" aria-label="Zoom in" title="Zoom in" onClick={() => mapRef.current?.zoomIn()}><Plus size={16} /></button>
        <button type="button" aria-label="Zoom out" title="Zoom out" onClick={() => mapRef.current?.zoomOut()}><Minus size={16} /></button>
      </div>
      <Legend />
    </div>
  );
}

function setData(map: MLMap | null, id: string, data: FC) {
  const source = map?.getSource(id) as GeoJSONSource | undefined;
  source?.setData(data as Parameters<GeoJSONSource['setData']>[0]);
}

/** Hover card built with DOM nodes (no HTML strings: names come from data). */
function tooltip(p: Record<string, string>): HTMLElement {
  const root = document.createElement('div');
  const title = document.createElement('strong');
  title.textContent = p.name;
  root.append(title);
  const line = (text: string) => { const d = document.createElement('div'); d.textContent = text; root.append(d); };
  if (p.kind === 'building') {
    line(`${p.risk} risk · net ${p.net}`);
    if (p.driver) line(p.driver);
  } else {
    line(`Substation · ${p.driver}`);
  }
  return root;
}
