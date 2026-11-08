import { useEffect, useRef, useState } from "react";
import Map, { type MapRef } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { useBuildings, useDemoState } from "../../shared/queries";
import { useUIStore } from "../../shared/ui-store";
import { MAP_STYLE, OFFLINE_STYLE, viewFor } from "./geo";
import HazardLayers from "./hazards";
import { BuildingLayer, PowerLayer } from "./markers";
import { Disclaimer, Legend, MapTools, TimelineControl } from "./chrome";
import "./map.css";

export default function MapView() {
  const mapRef = useRef<MapRef>(null);
  const snowCanvas = useRef<HTMLCanvasElement>(null);
  const ready = useRef(false);
  const demo = useDemoState();
  useBuildings();
  const { layers } = useUIStore();
  const scenarioId = demo.data?.scenario_id;
  const hour = demo.data?.step_hour;
  const scenarioRef = useRef(scenarioId);
  scenarioRef.current = scenarioId;
  const [labels, setLabels] = useState(true);
  const [style, setStyle] = useState<string | typeof OFFLINE_STYLE>(MAP_STYLE);
  const [hoverId, setHoverId] = useState<string | null>(null);

  const fly = (duration: number) => {
    const map = mapRef.current?.getMap();
    if (!map) return false;
    const view = viewFor(scenarioRef.current);
    const center = map.getCenter();
    const same = Math.abs(center.lat - view.latitude) < 0.05 && Math.abs(center.lng - view.longitude) < 0.05;
    map.flyTo({
      center: [view.longitude, view.latitude],
      zoom: view.zoom,
      pitch: 0,
      bearing: 0,
      duration: same ? 0 : duration,
      essential: true,
    });
    return true;
  };

  useEffect(() => {
    let cancel = false;
    if (!MAP_STYLE.startsWith("http")) return;
    fetch(MAP_STYLE)
      .then((response) => {
        if (!response.ok) throw new Error(String(response.status));
      })
      .catch(() => {
        if (!cancel) setStyle(OFFLINE_STYLE);
      });
    return () => {
      cancel = true;
    };
  }, []);

  useEffect(() => {
    const view = viewFor(scenarioId);
    let last = 0;
    const id = window.setInterval(() => {
      const map = mapRef.current?.getMap();
      if (!map) return;
      const center = map.getCenter();
      const arrived = Math.abs(center.lat - view.latitude) < 0.08 && Math.abs(center.lng - view.longitude) < 0.08;
      if (arrived) {
        window.clearInterval(id);
        return;
      }
      const now = performance.now();
      if (now - last < 900) return;
      last = now;
      map.flyTo({ center: [view.longitude, view.latitude], zoom: view.zoom, duration: 800, essential: true });
    }, 200);
    const stop = window.setTimeout(() => window.clearInterval(id), 5000);
    return () => {
      window.clearInterval(id);
      window.clearTimeout(stop);
    };
  }, [scenarioId]);

  const initial = viewFor(scenarioId);
  return (
    <div className="storm-map">
      <Map
        ref={mapRef}
        initialViewState={{ longitude: initial.longitude, latitude: initial.latitude, zoom: initial.zoom }}
        mapStyle={style}
        style={{ width: "100%", height: "100%" }}
        keyboard={false}
        attributionControl
        onLoad={() => {
          ready.current = true;
          fly(0);
        }}
        onMove={(event) => {
          const next = event.viewState.zoom >= 10;
          setLabels((current) => (current === next ? current : next));
        }}
      >
        {layers.hazard && <HazardLayers hour={hour} mapRef={mapRef} snowCanvas={snowCanvas} />}
        <BuildingLayer hour={hour} labels={labels} hoverId={hoverId} onHover={setHoverId} />
        <PowerLayer hoverId={hoverId} />
      </Map>
      <canvas ref={snowCanvas} className="snow-canvas" aria-hidden="true" />
      <TimelineControl />
      <MapTools mapRef={mapRef} />
      <Legend hour={hour} />
      <Disclaimer />
    </div>
  );
}
