import { HomeScreenHelp, MobileConnection, MobileNavigation, registerHomeScreenWorker, usePhoneLayout } from "./shared/mobile";
import DemoReset from "./shared/DemoReset";
import TermHelp from "./shared/TermHelp";
import MapView from "./modules/map";
import SimulationBuilder from "./modules/simulation";
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
  const phone = usePhoneLayout();
  useEffect(registerHomeScreenWorker, []);
  const scenarios = useScenarios();
  const state = useDemoState();
  const summary = useSummary();
  const load = useLoadScenario();
  useEffect(() => {
    selectBuilding(null);
    setPanelView("overview");
  }, [state.data?.scenario_id]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [mobileLegend, setMobileLegend] = useState(false);
  useEffect(() => {
    if (selectedBuildingId || panelView !== "overview") setDrawerOpen(true);
  }, [selectedBuildingId, panelView]);
  useEffect(() => {
    if (phone && panelView === "messages") { setPanelView("overview"); setDrawerOpen(false); }
  }, [phone, panelView]);
  useEffect(() => {
    if (!phone || !drawerOpen) return;
    const panel = document.getElementById("portfolio-panel");
    if (panel) panel.scrollTop = 0;
  }, [phone, drawerOpen, panelView]);
  const showMap = () => {
    setDrawerOpen(false);
    if (phone) requestAnimationFrame(() => document.querySelector<HTMLButtonElement>(".mobile-navigation button")?.focus());
  };
  const openView = (view: PanelView) => {
    setPanelView(view);
    setDrawerOpen(true);
  };
  return (
    <div className="app-shell" data-mobile-panel={phone && drawerOpen} data-mobile-legend={mobileLegend}>
      <a className="skip-link" href="#panel-content" onClick={() => phone && openView("overview")}>
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
        <div className="desktop-simulation-tools"><SimulationBuilder /><DemoReset /></div>
        <HomeScreenHelp />
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
            <small><TermHelp term="Estimated loss" /></small>
            <strong>
              {summary.data?.data_quality === "unknown" ? "Unknown" : summary.data ? money(summary.data.net_exposure_cents) : "—"}
            </strong>
          </div>
          <div>
            <small><TermHelp term="Avoided" /></small>
            <strong>
              {summary.data?.data_quality === "unknown" ? "Unknown" : summary.data ? money(summary.data.avoided_cents) : "—"}
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
      {phone && <><MobileConnection serviceError={state.isError || summary.isError} /><div className="mobile-context">
        <div>Estimated loss<strong>{summary.data?.data_quality === "unknown" ? "Unknown" : summary.data ? money(summary.data.net_exposure_cents) : "Unavailable"}</strong></div>
        <div>{state.data ? `${state.data.phase} · ${state.data.step_hour}h` : "Loading scenario"}<br />{state.dataUpdatedAt ? `Synced ${new Date(state.dataUpdatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · ${state.data?.scenario_id.startsWith("live") ? "live source" : "simulated impact"}` : "Awaiting response service"}</div>
      </div></>}
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
          data-view={panelView}
        >
          {phone && <div className="mobile-panel-heading"><strong>{({ fixfirst: "Fix-First", workorders: "Work Orders", help: "Help Sites", building: "Building details", buildings: "Buildings", overview: "Portfolio & layers", reports: "Reports", messages: "Portfolio" })[panelView]}</strong><Button variant="outline" onClick={showMap}>Back to map</Button></div>}
          <Panel onClose={() => setDrawerOpen(false)} />
        </aside>
        <main className="map-slot" aria-label="Map workspace" aria-hidden={phone && drawerOpen ? true : undefined} onClickCapture={event => {
          if (event.target instanceof Element && event.target.closest("[data-open-panel], [data-building-id], .response-details")) setDrawerOpen(true);
        }}>
          <MapView />
          {phone && <Button variant="outline" className="mobile-key-button" aria-label="Map key" aria-pressed={mobileLegend} onClick={() => setMobileLegend(!mobileLegend)}>Key</Button>}
          <div className="map-note">
            Illustrative hazards · Synthetic buildings and dollar figures
          </div>
          <Tooltip content="Map layers can be changed in the portfolio panel">
            <Button
              variant="outline"
              className="map-layer-button"
              aria-label="Open map layers in portfolio panel"
              onClick={() => {
                setPanelView("overview");
                setDrawerOpen(true);
                window.dispatchEvent(new Event("storm:open-layers"));
              }}
            >
              <Layers size={20} />
            </Button>
          </Tooltip>
        </main>
      </div>
      {phone && <MobileNavigation view={panelView} panelOpen={drawerOpen} onMap={showMap} onView={openView} />}
    </div>
  );
}
