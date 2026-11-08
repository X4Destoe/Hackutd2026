import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Layer, Marker, Source } from "react-map-gl/maplibre";
import { Check, Zap } from "lucide-react";
import { api, type Model } from "../../shared/api";
import { money, riskColor, type RiskLevel } from "../../shared/format";
import { useBuildings, useUtilities } from "../../shared/queries";
import { useUIStore } from "../../shared/ui-store";
import { useMapImpact } from "./data";
import { EMPTY } from "./geo";

function useQuiet<T>(key: string, load: (signal: AbortSignal) => Promise<T>, empty: T) {
  return useQuery({
    queryKey: [key, "map"],
    queryFn: async ({ signal }) => {
      try {
        return await load(signal);
      } catch {
        return empty;
      }
    },
    retry: false,
  });
}

function markerSize(cents: number, minSqrt: number, maxSqrt: number) {
  if (maxSqrt <= minSqrt) return 15;
  const t = (Math.sqrt(Math.max(cents, 0)) - minSqrt) / (maxSqrt - minSqrt);
  return 8 + Math.min(1, Math.max(0, t)) * 14;
}

export function BuildingLayer({ hour, labels, hoverId, onHover }: {
  hour?: number;
  labels: boolean;
  hoverId: string | null;
  onHover: (id: string | null) => void;
}) {
  const buildings = useBuildings();
  const impact = useMapImpact(hour);
  const { selectedBuildingId, selectBuilding, layers } = useUIStore();
  const plans = useQuiet("plans", (signal) => api.plans({}, signal), [] as Model<"Plan">[]);
  const orders = useQuiet("workOrders", (signal) => api.workOrders(undefined, signal), [] as Model<"WorkOrder">[]);
  const rows = buildings.data ?? [];
  const byImpact = useMemo(() => new Map((impact.data ?? []).map((item) => [item.building_id, item])), [impact.data]);
  const approved = useMemo(() => {
    const ids = new Set<string>();
    for (const plan of plans.data ?? []) {
      if (plan.status === "approved" || plan.status === "executing") ids.add(plan.building_id);
    }
    return ids;
  }, [plans.data]);
  const ordersByBuilding = useMemo(() => {
    const grouped = new Map<string, Model<"WorkOrder">[]>();
    for (const order of orders.data ?? []) {
      const list = grouped.get(order.building_id) ?? [];
      list.push(order);
      grouped.set(order.building_id, list);
    }
    return grouped;
  }, [orders.data]);
  const span = useMemo(() => {
    const roots = rows.map((building) => Math.sqrt(Math.max(building.replacement_value_cents, 0)));
    return { min: Math.min(...roots, 0), max: Math.max(...roots, 0) };
  }, [rows]);
  if (!layers.buildings) return null;
  return (
    <>
      {rows.map((building) => {
        const item = byImpact.get(building.id);
        const risk = (item?.risk ?? "none") as RiskLevel;
        const net = item?.money.net_exposure_cents;
        const size = markerSize(building.replacement_value_cents, span.min, span.max);
        const selected = selectedBuildingId === building.id;
        const siteOrders = ordersByBuilding.get(building.id) ?? [];
        const open = siteOrders.filter((order) => order.status !== "done");
        const blocked = siteOrders.some((order) => order.status === "blocked");
        const done = siteOrders.length > 0 && open.length === 0;
        const badgeCount = done ? siteOrders.length : open.length;
        const badgeColor = blocked ? "#dc2626" : done ? "#16834a" : "#334155";
        const title = net == null ? building.name : `${building.name} · ${money(net)}`;
        return (
          <Marker key={building.id} longitude={building.lon} latitude={building.lat} anchor="center">
            <span
              className="bldg-wrap"
              onMouseEnter={() => onHover(building.id)}
              onMouseLeave={() => onHover(hoverId === building.id ? null : hoverId)}
              onClick={(event) => {
                event.stopPropagation();
                selectBuilding(building.id);
              }}
            >
            <button
              type="button"
              className={`bldg${selected ? " selected" : ""}${approved.has(building.id) ? " approved" : ""}`}
              style={{ width: size, height: size, background: riskColor(risk) }}
              aria-label={`${building.name}, ${risk}${net == null ? "" : `, ${money(net)} net exposure`}`}
              aria-pressed={selected}
              onFocus={() => onHover(building.id)}
              onBlur={() => onHover(null)}
              onClick={(event) => {
                event.stopPropagation();
                selectBuilding(building.id);
              }}
            >
              {layers.workorders && badgeCount > 0 && (
                <span className="wo-badge" style={{ background: badgeColor }}>{badgeCount}</span>
              )}
              {approved.has(building.id) && <Check className="approved-mark" size={11} strokeWidth={3} aria-hidden />}
            </button>
            {labels && <span className="bldg-label">{title}</span>}
            {hoverId === building.id && (
              <span className="map-tip" role="tooltip">
                <strong>{building.name}</strong>
                <span>{net == null ? "Exposure loading" : `${money(net)} net`}</span>
                <span className="tip-risk">{risk}</span>
                <span>{item?.drivers?.[0] ?? "No driver reported"}</span>
              </span>
            )}
            </span>
          </Marker>
        );
      })}
    </>
  );
}

export function PowerLayer({ hoverId }: { hoverId: string | null }) {
  const buildings = useBuildings();
  const utilities = useUtilities();
  const { selectedBuildingId, layers } = useUIStore();
  const focusId = hoverId ?? selectedBuildingId;
  const link = useMemo(() => {
    if (!layers.power) return EMPTY;
    const building = (buildings.data ?? []).find((item) => item.id === focusId);
    const utility = (utilities.data ?? []).find((item) => item.id === building?.utility_node_id);
    if (!building || !utility) return EMPTY;
    return {
      type: "FeatureCollection" as const,
      features: [{
        type: "Feature" as const,
        properties: {},
        geometry: { type: "LineString" as const, coordinates: [[building.lon, building.lat], [utility.lon, utility.lat]] },
      }],
    };
  }, [buildings.data, utilities.data, focusId, layers.power]);
  if (!layers.power) return null;
  const substations = (utilities.data ?? []).filter((utility) => utility.kind === "substation");
  return (
    <>
      <Source id="power-link" type="geojson" data={link}>
        <Layer id="power-link-line" type="line" paint={{ "line-color": "#b45309", "line-width": 2, "line-dasharray": [1.2, 1.2] }} />
      </Source>
      {substations.map((utility) => (
        <Marker key={utility.id} longitude={utility.lon} latitude={utility.lat} anchor="center">
          <span className={`sub${utility.down ? " down" : ""}`} title={`${utility.name}${utility.down ? ", down" : ""}`}>
            <Zap size={8} aria-hidden />
            <span className="sr-only">{utility.name}{utility.down ? ", down" : ""}</span>
          </span>
        </Marker>
      ))}
    </>
  );
}
