import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api } from './api';
import { invalidateKeys, scenarioKeys } from './queries';
export const eventQueries: Record<string, readonly string[]> = {
  'scenario.loaded': scenarioKeys, 'timeline.changed': scenarioKeys,
  'impact.updated': ['impact', 'summary'], 'plans.updated': ['plans', 'fixFirst', 'summary'],
  'plan.changed': ['plans', 'fixFirst', 'summary'], 'workorder.changed': ['workOrders', 'plans'],
  'message.sent': ['messages', 'messagingStatus'], 'message.received': ['messages', 'messagingStatus'],
  'resources.changed': ['resources', 'referrals'], 'referral.changed': ['resources', 'referrals'], 'report.created': ['reports'],
};
export type LiveEvent = { type: string; data: unknown; receivedAt: number };
/** Mount once below QueryClientProvider. Native EventSource retries on disconnect. */
export function useEvents() {
  const client = useQueryClient();
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    const source = api.events();
    const handlers = Object.entries(eventQueries).map(([type, keys]) => {
      const handler = (event: MessageEvent) => {
        let data: unknown;
        try { data = JSON.parse(event.data); } catch { return; }
        setEvents(previous => [...previous.slice(-99), { type, data, receivedAt: Date.now() }]);
        void invalidateKeys(client, keys);
      };
      source.addEventListener(type, handler);
      return { type, handler };
    });
    source.onopen = () => { setConnected(true); void client.invalidateQueries(); };
    source.onerror = () => setConnected(false);
    return () => { handlers.forEach(({ type, handler }) => source.removeEventListener(type, handler)); source.close(); };
  }, [client]);
  return { events, connected };
}
