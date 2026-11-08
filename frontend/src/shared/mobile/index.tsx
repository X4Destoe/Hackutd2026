import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, ListChecks, Map, MapPin, Wrench } from 'lucide-react';
import { Button, Dialog } from '../ui';
import { api } from '../api';
import type { PanelView } from '../ui-store';
import './mobile.css';

export function usePhoneLayout() {
  const client = useQueryClient();
  const [phone, setPhone] = useState(() => window.matchMedia('(max-width: 900px), (max-width: 1024px) and (pointer: coarse)').matches);
  useEffect(() => {
    const query = window.matchMedia('(max-width: 900px), (max-width: 1024px) and (pointer: coarse)');
    const update = () => setPhone(query.matches);
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);
  useEffect(() => {
    if (!phone) return;
    const previous = client.getDefaultOptions();
    // An offline approval/update must fail visibly, never wait silently to send on reconnect.
    client.setDefaultOptions({ ...previous, mutations: { ...previous.mutations, networkMode: 'always', retry: false } });
    return () => client.setDefaultOptions(previous);
  }, [client, phone]);
  return phone;
}

export function HomeScreenHelp() {
  return <div className="mobile-install"><Dialog trigger={<Button variant="outline" aria-label="Add to Home Screen instructions"><Download size={19} /></Button>} title="Keep Storm on your Home Screen">
    <p>On your iPhone, open this site in Safari.</p>
    <ol className="mobile-install-steps"><li>Tap the Share button.</li><li>Choose <strong>Add to Home Screen</strong>.</li><li>Turn on <strong>Open as Web App</strong> if offered, then tap <strong>Add</strong>.</li></ol>
    <p>Open the Storm icon for the map and response tools. An internet connection and the running response service are required for current information.</p>
  </Dialog></div>;
}

export function MobileConnection({ serviceError }: { serviceError: boolean }) {
  const [online, setOnline] = useState(navigator.onLine);
  const health = useQuery({ queryKey: ['mobileHealth'], queryFn: ({ signal }) => api.health(signal), refetchInterval: 15_000, retry: false });
  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => { window.removeEventListener('online', update); window.removeEventListener('offline', update); };
  }, []);
  if (online && !serviceError && !health.isError && health.data?.ok !== false) return null;
  return <p className="mobile-connection" role="alert">{!online ? 'Offline. Displayed information may be out of date. Reconnect before taking action.' : 'Response service unavailable. Displayed information may be out of date.'}</p>;
}

export function MobileNavigation({ view, panelOpen, onMap, onView }: {
  view: PanelView; panelOpen: boolean; onMap: () => void; onView: (view: PanelView) => void;
}) {
  const items = [['map', 'Map', Map], ['fixfirst', 'Fix-First', ListChecks], ['workorders', 'Work Orders', Wrench], ['help', 'Help Sites', MapPin]] as const;
  return <nav className="mobile-navigation" aria-label="Mobile response tools">{items.map(([key, label, Icon]) => {
    const active = key === 'map' ? !panelOpen : panelOpen && view === key;
    return <button key={key} type="button" aria-pressed={active} onClick={() => key === 'map' ? onMap() : onView(key)}><Icon size={22} /><span>{label}</span></button>;
  })}</nav>;
}

export function registerHomeScreenWorker() {
  if (import.meta.env.PROD && 'serviceWorker' in navigator && window.isSecureContext) {
    // Cache only the offline explanation, never API responses, map tiles or emergency records.
    void navigator.serviceWorker.register('/sw.js').catch(() => { /* Home Screen launch still works without offline fallback. */ });
  }
}
