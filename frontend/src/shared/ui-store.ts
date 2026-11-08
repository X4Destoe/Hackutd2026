import { createContext, createElement, useContext, useState, type ReactNode } from 'react';
export type PanelView = 'overview' | 'buildings' | 'building' | 'fixfirst' | 'workorders' | 'help' | 'reports' | 'messages';
export type Layer = 'hazard' | 'buildings' | 'power' | 'workorders' | 'help' | 'messages';
export const defaultLayers: Record<Layer, boolean> = { hazard: true, buildings: true, power: true, workorders: true, help: true, messages: false };
function useStore() {
  const [selectedBuildingId, setSelectedBuildingId] = useState<string | null>(null);
  const [panelView, setPanelView] = useState<PanelView>('overview');
  const [layers, setLayers] = useState({ ...defaultLayers });
  const selectBuilding = (id: string | null) => { setSelectedBuildingId(id); setPanelView(id ? 'building' : 'buildings'); };
  const toggleLayer = (layer: Layer) => setLayers(current => ({ ...current, [layer]: !current[layer] }));
  const setAllLayers = (enabled: boolean) => setLayers(current => Object.fromEntries(Object.keys(current).map(key => [key, enabled])) as Record<Layer, boolean>);
  return { selectedBuildingId, setSelectedBuildingId, selectBuilding, panelView, setPanelView, layers, toggleLayer, setAllLayers };
}
const UIContext = createContext<ReturnType<typeof useStore> | null>(null);
export function UIProvider({ children }: { children: ReactNode }) { return createElement(UIContext.Provider, { value: useStore() }, children); }
export function useUIStore() { const state = useContext(UIContext); if (!state) throw new Error('useUIStore requires UIProvider'); return state; }
