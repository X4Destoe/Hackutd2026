import { useEffect, useRef } from "react";
import maplibregl, { type Map as MLMap } from "maplibre-gl";
import { useBuildings, useMessages, useResources, useWorkOrders } from "../../shared/queries";
import { useUIStore } from "../../shared/ui-store";
import "./activity.css";

/** HTML markers remain usable when remote style tiles or glyphs are unavailable. */
export default function ActivityLayers({ map, city }: { map: MLMap | null; city?: string }) {
  const sites = useResources(city);
  const orders = useWorkOrders();
  const messages = useMessages();
  const buildings = useBuildings();
  const { layers, selectBuilding, setPanelView } = useUIStore();
  const callbacks = useRef({ selectBuilding, setPanelView });
  callbacks.current = { selectBuilding, setPanelView };

  useEffect(() => {
    if (!map || !city) return;
    const markers: maplibregl.Marker[] = [];
    const add = (kind: string, id: string, lat: number, lon: number, text: string, label: string, status: string, click: () => void, offset: [number, number] = [0, 0]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `activity-pin activity-${kind} activity-${status}`;
      button.dataset.activityKind = kind;
      button.dataset.activityId = id;
      button.dataset.openPanel = "true";
      button.title = label;
      button.textContent = text;
      button.addEventListener("click", event => { event.stopPropagation(); click(); });
      markers.push(new maplibregl.Marker({ element: button, offset }).setLngLat([lon, lat]).addTo(map));
      // MapLibre supplies its generic label during construction; restore the useful record label afterward.
      button.setAttribute("aria-label", label);
    };
    if (layers.help) for (const site of sites.data ?? []) {
      if (site.city !== city) continue;
      add("help", site.id, site.lat, site.lon, site.status === "unsafe" ? "×" : "H",
        `${site.name}: ${site.status}, ${Math.max(0, site.capacity - site.used)} places available. Open Help Sites`,
        site.status, () => callbacks.current.setPanelView("help"), [-22, -24]);
    }
    for (const building of buildings.data ?? []) {
      if (building.city !== city) continue;
      const work = (orders.data ?? []).filter(order => order.building_id === building.id);
      if (layers.workorders && work.length) {
        const open = work.filter(order => order.status !== "done");
        const state = open.some(order => order.status === "blocked") ? "blocked" : open.length ? "active" : "done";
        add("workorders", building.id, building.lat, building.lon, `W ${open.length}`,
          `${building.name}: ${open.length} open work orders, ${open.filter(order => order.status === "blocked").length} blocked, ${work.length - open.length} done. Open Work Orders`, state,
          () => { callbacks.current.selectBuilding(building.id); callbacks.current.setPanelView("workorders"); }, [22, -24]);
      }
      const contacts = new Set([building.onsite_party_id, ...(building.tenants ?? []).map(tenant => tenant.contact_party_id ?? tenant.id)]);
      const linked = (messages.data ?? []).filter(message => contacts.has(message.party_id) || work.some(order => order.id === message.work_order_id));
      if (layers.messages && linked.length) add("messages", building.id, building.lat, building.lon, `T ${linked.length}`,
        `${building.name}: ${linked.length} linked texts, ${linked.filter(message => message.status === "failed").length} failed. Open Texts`, linked.some(message => message.status === "failed") ? "blocked" : "active",
        () => { callbacks.current.selectBuilding(building.id); callbacks.current.setPanelView("messages"); }, [22, 24]);
    }
    return () => markers.forEach(marker => marker.remove());
  }, [map, city, layers.help, layers.workorders, layers.messages, sites.data, buildings.data, orders.data, messages.data]);

  const currentOrders = orders.data?.filter(order => buildings.data?.some(building => building.id === order.building_id && building.city === city));
  return <aside className="map-activity" aria-label="Operational map layers">
    {layers.help && <button data-open-panel onClick={() => setPanelView("help")}>
      <strong>Help sites</strong><span>{sites.isError ? "Unavailable · open details" : sites.isPending ? "Loading…" : `${sites.data?.length ?? 0} sites · view capacity`}</span>
    </button>}
    {layers.workorders && <button data-open-panel onClick={() => setPanelView("workorders")}>
      <strong>Work orders</strong><span>{orders.isError ? "Unavailable · open details" : orders.isPending ? "Loading…" : `${currentOrders?.filter(order => order.status !== "done").length ?? 0} open · view tasks`}</span>
    </button>}
    {layers.messages && <button data-open-panel onClick={() => setPanelView("messages")}>
      <strong>Texts</strong><span>{messages.isError ? "Unavailable · open details" : messages.isPending ? "Loading…" : `${messages.data?.length ?? 0} messages · view inbox`}</span>
      <small>Pins show building-linked texts; inbox includes unlocated messages.</small>
    </button>}
  </aside>;
}
