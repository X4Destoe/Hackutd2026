import MapView from "./modules/map";
import { useEffect, useState } from "react";
import {
  Building2,
  CloudRain,
  FileText,
  Layers,
  ListChecks,
  MapPin,
  Menu,
  MessageSquare,
  Radio,
  Wrench,
  X,
  Zap,
} from "lucide-react";
import { Button, Tooltip } from "./shared/ui";
import Panel from "./modules/panel";
import {
  useScenarios,
  useDemoState,
  useSummary,
  useLoadScenario,
} from "./shared/queries";
import { money } from "./shared/format";
import { useUIStore, type PanelView } from "./shared/ui-store";
const navigation = [
  ["fixfirst", "Fix-First", ListChecks],
  ["workorders", "Work Orders", Wrench],
  ["help", "Help Sites", MapPin],
  ["messages", "Texts", MessageSquare],
  ["reports", "Reports", FileText],
] as const;
export default function App() {
  const { panelView, setPanelView, selectBuilding, selectedBuildingId } = useUIStore();
  const scenarios = useScenarios();
  const state = useDemoState();
  const summary = useSummary();
  const load = useLoadScenario();
  useEffect(() => {
    selectBuilding(null);
    setPanelView("overview");
  }, [state.data?.scenario_id]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  useEffect(() => {
    if (selectedBuildingId || panelView !== "overview") setDrawerOpen(true);
  }, [selectedBuildingId, panelView]);
  const openView = (view: PanelView) => {
    setPanelView(view);
    setDrawerOpen(true);
  };
  return (
    <div className="app-shell">
      <a className="skip-link" href="#panel-content">
        Skip to panel
      </a>
      <header className="top-bar">
        <div className="brand">
          <svg width="32" height="32" viewBox="0 0 32 32" aria-hidden="true">
            <rect width="32" height="32" fill="#1f7a45" />
            <path
              d="M6 8.6h20M9 14.2h14M12 19.8h8M14.5 25.4h3"
              stroke="white"
              strokeWidth="3.2"
            />
          </svg>
          <div>
            <strong>Operation Storm</strong>
            <small>Portfolio disaster impact</small>
          </div>
        </div>
        <label className="scenario-label">
          <span className="sr-only">Disaster scenario</span>
          <select
            disabled={!scenarios.data || load.isPending}
            value={state.data?.scenario_id ?? ""}
            onChange={(e) => load.mutate(e.target.value)}
            aria-describedby="scenario-status"
          >
            <option value="" disabled>
              Select a scenario
            </option>
            {scenarios.data?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} · {s.city}
              </option>
            ))}
          </select>
        </label>
        <nav aria-label="Portfolio tools">
          {navigation.map(([view, label, Icon]) => (
            <Button
              key={view}
              aria-pressed={panelView === view}
              onClick={() => openView(view)}
            >
              <Icon size={16} />
              <span>{label}</span>
            </Button>
          ))}
        </nav>
        <div className="portfolio-totals" aria-label="Portfolio totals">
          <div>
            <small title="Estimated financial loss after insurance and approved actions">Estimated loss</small>
            <strong>
              {summary.data ? money(summary.data.net_exposure_cents) : "—"}
            </strong>
          </div>
          <div>
            <small>Avoided</small>
            <strong>
              {summary.data ? money(summary.data.avoided_cents) : "—"}
            </strong>
          </div>
        </div>
        <Button
          variant="outline"
          className="drawer-toggle"
          onClick={() => setDrawerOpen(!drawerOpen)}
          aria-label="Toggle portfolio panel"
          aria-expanded={drawerOpen}
          aria-controls="portfolio-panel"
        >
          <Menu size={20} />
        </Button>
      </header>
      {load.isError && (
        <p role="alert">Could not switch scenario. Please retry.</p>
      )}
      <div className="workspace">
        {drawerOpen && (
          <button
            className="drawer-backdrop"
            aria-label="Close portfolio panel"
            onClick={() => setDrawerOpen(false)}
          />
        )}
        <aside
          id="portfolio-panel"
          className={`left-panel ${drawerOpen ? "drawer-open" : ""}`}
          aria-label="Portfolio panel"
        >
          <Panel onClose={() => setDrawerOpen(false)} />
        </aside>
        <main className="map-slot" aria-label="Map workspace" onClickCapture={event => {
          if (event.target instanceof Element && event.target.closest("[data-open-panel], [data-building-id], .response-details")) setDrawerOpen(true);
        }}>
          <MapView />
          <div className="map-note">
            Illustrative hazards · Synthetic buildings and dollar figures
          </div>
          <Tooltip content="Map layers can be changed in the portfolio panel">
            <Button
              variant="outline"
              className="map-layer-button"
              aria-label="Open map layers in portfolio panel"
              onClick={() => {
                setDrawerOpen(true);
              }}
            >
              <Layers size={20} />
            </Button>
          </Tooltip>
        </main>
      </div>
    </div>
  );
}
