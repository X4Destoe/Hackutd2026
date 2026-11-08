import { useState } from 'react';
import { Building2, CloudRain, FileText, Layers, ListChecks, MapPin, Menu, MessageSquare, Radio, Wrench, X, Zap } from 'lucide-react';
import { Button, Card, Tooltip } from './shared/ui';
import { useUIStore, type Layer, type PanelView } from './shared/ui-store';
const navigation = [ ['fixfirst', 'Fix-First', ListChecks], ['workorders', 'Work Orders', Wrench], ['help', 'Help Sites', MapPin], ['messages', 'Texts', MessageSquare], ['reports', 'Reports', FileText] ] as const;
const layerRows = [ ['hazard', 'Hazard overlay', CloudRain], ['buildings', 'Buildings by $ at risk', Building2], ['power', 'Power grid', Zap], ['help', 'Help sites and residents', MapPin], ['workorders', 'Work orders', Wrench], ['messages', 'Messages', MessageSquare] ] as const;
const titles: Record<PanelView, string> = { overview: 'Portfolio overview', buildings: 'Buildings', building: 'Building detail', fixfirst: 'Fix-First', workorders: 'Work Orders', help: 'Help Sites', reports: 'Reports', messages: 'Texts' };
export default function App() {
  const { panelView, setPanelView, layers, toggleLayer, setAllLayers } = useUIStore();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const openView = (view: PanelView) => { setPanelView(view); setDrawerOpen(true); };
  return <div className="app-shell">
    <a className="skip-link" href="#panel-content">Skip to panel</a>
    <header className="top-bar">
      <div className="brand"><svg width="32" height="32" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" fill="#1f7a45"/><path d="M6 8.6h20M9 14.2h14M12 19.8h8M14.5 25.4h3" stroke="white" strokeWidth="3.2"/></svg><div><strong>Operation Storm</strong><small>Portfolio disaster impact</small></div></div>
      <label className="scenario-label"><span className="sr-only">Disaster scenario</span><select disabled aria-describedby="scenario-status"><option>Scenarios awaiting connection</option></select></label>
      <nav aria-label="Portfolio tools">{navigation.map(([view, label, Icon]) => <Button key={view} aria-pressed={panelView === view} onClick={() => openView(view)}><Icon size={16}/><span>{label}</span></Button>)}</nav>
      <div className="portfolio-totals" aria-label="Portfolio totals awaiting connection"><div><small>Net exposure</small><strong>—</strong></div><div><small>Avoided</small><strong>—</strong></div></div>
      <Button variant="outline" className="drawer-toggle" onClick={() => setDrawerOpen(!drawerOpen)} aria-label="Toggle portfolio panel" aria-expanded={drawerOpen} aria-controls="portfolio-panel"><Menu size={20}/></Button>
    </header>
    <div className="workspace">
      {drawerOpen && <button className="drawer-backdrop" aria-label="Close portfolio panel" onClick={() => setDrawerOpen(false)}/>}
      <aside id="portfolio-panel" className={`left-panel ${drawerOpen ? 'drawer-open' : ''}`} aria-label="Portfolio panel">
        <div className="scenario-hero"><div className="hero-skyline" aria-hidden="true"/><div className="hero-copy"><div className="hero-heading"><span className="eyebrow">Disaster readiness</span><Button variant="ghost" className="drawer-close" aria-label="Close portfolio panel" onClick={() => setDrawerOpen(false)}><X size={18}/></Button></div><h1>See the storm.<br/>Act before it hits.</h1><p id="scenario-status">Connect a scenario to see its forecast, portfolio impact and response priorities.</p></div></div>
        <nav className="panel-tabs" aria-label="Portfolio views">{(['overview','buildings','help'] as const).map(view => <button key={view} aria-pressed={panelView === view} onClick={() => setPanelView(view)}>{view === 'help' ? 'Help' : titles[view].replace('Portfolio ', '')}</button>)}</nav>
        <section className="layer-section" aria-label="Map layers"><div className="layer-heading"><span>Map layers</span><div><button onClick={() => setAllLayers(true)}>Select all</button><span aria-hidden="true"> / </span><button onClick={() => setAllLayers(false)}>Clear</button></div></div>{layerRows.map(([key, label, Icon]) => <label className="layer-row" key={key}><span className={`layer-icon layer-${key}`}><Icon size={17}/></span><span>{label}</span><input type="checkbox" checked={layers[key]} onChange={() => toggleLayer(key as Layer)}/></label>)}</section>
        <section id="panel-content" className="panel-content" tabIndex={-1} aria-labelledby="panel-title"><h2 id="panel-title">{titles[panelView]}</h2><Card><div className="placeholder-icon"><Radio size={22}/></div><h3>{panelView === 'overview' ? 'Your portfolio, in focus' : titles[panelView]}</h3><p>{panelView === 'overview' ? 'Building exposure, avoided losses and the highest-value actions will appear here when the portfolio is connected.' : 'This workspace is ready for its module. Live records will appear when the service is connected.'}</p><span className="status-label">Awaiting data connection</span></Card></section>
        <footer className="panel-footer">Operation Storm <span>Portfolio disaster impact</span></footer>
      </aside>
      <main className="map-slot" aria-label="Map workspace"><div className="map-grid" aria-hidden="true"/><div className="map-placeholder"><Layers size={30}/><h2>Portfolio map</h2><p>Scenario hazards, buildings and response layers will appear here.</p><span className="status-label">Map module pending</span></div><div className="map-note">Illustrative hazards · Synthetic buildings and dollar figures</div><Tooltip content="Map layers can be changed in the portfolio panel"><Button variant="outline" className="map-layer-button" aria-label="Open map layers in portfolio panel" onClick={() => { setDrawerOpen(true); }}><Layers size={20}/></Button></Tooltip></main>
    </div>
  </div>;
}
