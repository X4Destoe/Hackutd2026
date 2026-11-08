import VisualGuide from "../../shared/VisualGuide";
import { cityPhoto } from "../../shared/city-photos";
import HelpSites from "./views/community/HelpSites";
import Reports from "./views/community/Reports";
import Messages from "./views/community/Messages";
import "./views/community/community.css";
import { useEffect, useState } from "react";
import {
  Building2,
  CloudRain,
  MapPin,
  MessageSquare,
  Search,
  Wrench,
  X,
  Zap,
} from "lucide-react";
import {
  useBuildings,
  useDemoState,
  useTimeline,
  useScenarios,
  useSummary,
} from "../../shared/queries";
import { useUIStore, type Layer } from "../../shared/ui-store";
import { hours, money, phaseColor } from "../../shared/format";
import { Button } from "../../shared/ui";
import Overview from "./views/Overview";
import FixFirst from "./views/actions/FixFirst";
import WorkOrders from "./views/actions/WorkOrders";
import Buildings from "./views/Buildings";
import BuildingDetail from "./views/BuildingDetail";
import "./panel.css";
const rows = [
  ["hazard", "Hazard overlay", CloudRain],
  ["buildings", "Buildings by $ at risk", Building2],
  ["power", "Power grid", Zap],
  ["help", "Help sites and residents", MapPin],
  ["workorders", "Work orders", Wrench],
  ["messages", "Messages", MessageSquare],
] as const;
/** Lives inside the app's aside. Map and panel share selection through useUIStore. */
export default function Panel({ onClose }: { onClose?: () => void }) {
  const {
    panelView,
    setPanelView,
    selectBuilding,
    layers,
    toggleLayer,
    setAllLayers,
  } = useUIStore();
  const [layersOpen, setLayersOpen] = useState(false);
  useEffect(() => {
    const open = () => {
      setLayersOpen(true);
      document.querySelector(".layer-section")?.scrollIntoView({ block: "start" });
    };
    window.addEventListener("storm:open-layers", open);
    return () => window.removeEventListener("storm:open-layers", open);
  }, []);
  const [loadedPhoto, setLoadedPhoto] = useState("");
  const [failedPhoto, setFailedPhoto] = useState("");
  const state = useDemoState();
  const timeline = useTimeline();
  const scenarios = useScenarios();
  const summary = useSummary();
  const buildings = useBuildings();
  const [search, setSearch] = useState("");
  const scenario = scenarios.data?.find(
    (s) => s.id === state.data?.scenario_id,
  );
  const photo = cityPhoto(scenario?.city);
  const photoVisible = Boolean(
    photo && loadedPhoto === photo.src && failedPhoto !== photo.src,
  );
  useEffect(() => {
    setSearch("");
  }, [state.data?.scenario_id]);
  return (
    <>
      <div
        className={`scenario-hero panel-hero ${photoVisible ? "photo-present" : ""}`}
      >
        {photo && failedPhoto !== photo.src && (
          <img
            className="panel-city-photo"
            src={photo.src}
            alt=""
            aria-hidden="true"
            onLoad={() => setLoadedPhoto(photo.src)}
            onError={() => setFailedPhoto(photo.src)}
          />
        )}
        <div className="hero-skyline" aria-hidden="true" />
        <div className="hero-copy">
          <form
            className="building-search"
            role="search"
            onSubmit={(e) => {
              e.preventDefault();
              const first = buildings.data?.find((b) =>
                [b.name, ...(b.tenants ?? []).map((t) => t.name)].some((name) =>
                  name.toLowerCase().includes(search.toLowerCase()),
                ),
              );
              if (search && first) selectBuilding(first.id);
            }}
          >
            <Search size={15} />
            <input
              aria-label="Search building or tenant"
              placeholder="Search building, tenant…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPanelView("buildings");
              }}
            />
            {onClose && (
              <Button
                variant="ghost"
                className="drawer-close"
                aria-label="Close portfolio panel"
                onClick={onClose}
              >
                <X size={17} />
              </Button>
            )}
          </form>
          <span
            className="phase-label"
            style={{
              borderColor: state.data
                ? phaseColor(state.data.phase)
                : undefined,
            }}
          >
            {state.data
              ? `${state.data.phase} · ${hours(state.data.step_hour)}`
              : "Awaiting scenario"}
          </span>
          <h1>{scenario?.name ?? "Portfolio disaster impact"}</h1>
          <p className="hero-date">
            {scenario
              ? `${scenario.city} · ${scenario.date_label}`
              : "Connect a scenario to begin."}
          </p>
          <p id="scenario-status">
            {state.isError
              ? "Scenario data is unavailable. Please retry when the service reconnects."
              : (timeline.data?.find(
                  (step) => step.hour === state.data?.step_hour,
                )?.narrative ??
                (timeline.isError
                  ? "Scenario narrative is unavailable."
                  : "Loading scenario narrative…"))}
          </p>
          <div className="hero-metrics" aria-live="polite">
            <div>
              <span title="After insurance and approved actions">Estimated loss</span>
              <strong key={`net-${summary.data?.net_exposure_cents}`}>
                {summary.data?.data_quality === "unknown" ? "Unknown" : summary.data ? money(summary.data.net_exposure_cents) : "—"}
              </strong>
            </div>
            <div>
              <span>Avoided</span>
              <strong key={`avoided-${summary.data?.avoided_cents}`}>
                {summary.data?.data_quality === "unknown" ? "Unknown" : summary.data ? money(summary.data.avoided_cents) : "—"}
              </strong>
            </div>
          </div>
          {photoVisible && photo && (
            <small className="hero-photo-credit">{photo.credit}</small>
          )}
          <small className="hero-disclaimer">
            Footprints approximate · Portfolio and amounts synthetic
          </small>
        </div>
      </div>
      <nav className="panel-tabs" aria-label="Portfolio views">
        {(["overview", "buildings", "help"] as const).map((view) => (
          <button
            key={view}
            aria-pressed={panelView === view}
            onClick={() => setPanelView(view)}
          >
            {view === "help"
              ? "Help"
              : view === "overview"
                ? "Overview"
                : "Buildings"}
          </button>
        ))}
      </nav>
      <section className="layer-section" aria-label="Map layers">
        <div className="layer-heading">
          <button className="layer-disclosure" aria-expanded={layersOpen} aria-controls="map-layer-options" onClick={() => setLayersOpen(!layersOpen)}>Map layers <span aria-hidden="true">{layersOpen ? "−" : "+"}</span></button>
          {layersOpen && <div>
            <button onClick={() => setAllLayers(true)}>Select all</button>
            <span> / </span>
            <button onClick={() => setAllLayers(false)}>Clear</button>
          </div>}
        </div>
        {layersOpen && <div id="map-layer-options">{rows.map(([key, label, Icon]) => (
          <label key={key} className="layer-row">
            <span className={`layer-icon layer-${key}`}>
              <Icon size={16} />
            </span>
            <span>{label}</span>
            <input
              type="checkbox"
              checked={layers[key]}
              onChange={() => toggleLayer(key as Layer)}
            />
          </label>
        ))}</div>}
      </section>
      <section
        id="panel-content"
        className="panel-content"
        tabIndex={-1}
        aria-label="Portfolio content"
      >
        <VisualGuide view={panelView} />
        {panelView === "overview" ? (
          <Overview />
        ) : panelView === "buildings" ? (
          <Buildings search={search} city={scenario?.city} />
        ) : panelView === "building" ? (
          <BuildingDetail />
        ) : panelView === "help" ? (
          <HelpSites city={scenario?.city} />
        ) : panelView === "reports" ? (
          <Reports />
        ) : panelView === "messages" ? (
          <Messages />
        ) : panelView === "fixfirst" ? (
          <FixFirst />
        ) : (
          <WorkOrders />
        )}
      </section>
      <footer className="panel-footer">
        Operation Storm
        <span>
          {buildings.data ? `${buildings.data.length} buildings` : "Portfolio"}{" "}
          · {scenario?.city ?? "All cities"}
        </span>
      </footer>
    </>
  );
}
