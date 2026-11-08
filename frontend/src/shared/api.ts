import type { components } from './api-types';
type Schemas = components['schemas'];
export type Model<K extends keyof Schemas> = Schemas[K];
export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) { super(`API request failed (${status})`); this.name = 'ApiError'; }
}
function query(values: Record<string, string | number | undefined> = {}) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => { if (value !== undefined) params.set(key, String(value)); });
  return params.size ? `?${params}` : '';
}
async function request<T>(path: string, method = 'GET', body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api${path}`, { method, signal, headers: body === undefined ? undefined : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  if (!response.ok) { let detail: unknown; try { detail = await response.json(); } catch { detail = response.statusText; } throw new ApiError(response.status, detail); }
  return response.json() as Promise<T>;
}
const id = encodeURIComponent;
export type GeoJSONCollection = { type: 'FeatureCollection'; features: Array<{ type: 'Feature'; geometry: Record<string, unknown>; properties: Record<string, unknown> }> };
export type PlanFilter = { building_id?: string; status?: Model<'PlanStatus'> };
export type SimulatedMessage = { phone?: string; party_id?: string; text: string; media_url?: string };
export const api = {
  health: (signal?: AbortSignal) => request<{ ok: boolean }>('/health', 'GET', undefined, signal),
  contracts: (signal?: AbortSignal) => request<Model<'Contracts'>>('/_contracts', 'GET', undefined, signal),
  events: () => new EventSource('/api/events'),
  scenarios: (signal?: AbortSignal) => request<Model<'ScenarioMeta'>[]>('/scenarios', 'GET', undefined, signal),
  reset: (scenario_id?: string) => request<Model<'DemoState'>>('/demo/reset', 'POST', scenario_id ? { scenario_id } : {}),
  loadScenario: (scenarioId: string) => request<Model<'DemoState'>>(`/scenarios/${id(scenarioId)}/load`, 'POST'),
  demoState: (signal?: AbortSignal) => request<Model<'DemoState'>>('/demo/state', 'GET', undefined, signal),
  setHour: (hour: number) => request<Model<'DemoState'>>('/timeline', 'POST', { hour }),
  overlays: (hour?: number, signal?: AbortSignal) => request<GeoJSONCollection>(`/overlays${query({ hour })}`, 'GET', undefined, signal),
  buildings: (signal?: AbortSignal) => request<Model<'Building'>[]>('/buildings', 'GET', undefined, signal),
  utilities: (signal?: AbortSignal) => request<(Model<'UtilityNode'> & { down: boolean })[]>('/utilities', 'GET', undefined, signal),
  impact: (hour?: number, signal?: AbortSignal) => request<Model<'Impact'>[]>(`/impact${query({ hour })}`, 'GET', undefined, signal),
  impactFor: (buildingId: string, hour?: number, signal?: AbortSignal) => request<Model<'Impact'>>(`/impact/${id(buildingId)}${query({ hour })}`, 'GET', undefined, signal),
  summary: (signal?: AbortSignal) => request<Model<'PortfolioSummary'>>('/portfolio/summary', 'GET', undefined, signal),
  catalog: (signal?: AbortSignal) => request<Model<'ActionTemplate'>[]>('/actions/catalog', 'GET', undefined, signal),
  plans: (filter: PlanFilter = {}, signal?: AbortSignal) => request<Model<'Plan'>[]>(`/plans${query(filter)}`, 'GET', undefined, signal),
  approvePlan: (planId: string, by: string) => request<Model<'Plan'>>(`/plans/${id(planId)}/approve`, 'POST', { by }),
  rejectPlan: (planId: string, by: string) => request<Model<'Plan'>>(`/plans/${id(planId)}/reject`, 'POST', { by }),
  fixFirst: (limit = 10, community = false, signal?: AbortSignal) => request<Model<'FixFirstItem'>[]>(`/fix-first${query({ limit, community: community ? 1 : 0 })}`, 'GET', undefined, signal),
  workOrders: (building_id?: string, signal?: AbortSignal) => request<Model<'WorkOrder'>[]>(`/workorders${query({ building_id })}`, 'GET', undefined, signal),
  updateWorkOrder: (workOrderId: string, status: Model<'WorkOrderStatus'>, note?: string) => request<Model<'WorkOrder'>>(`/workorders/${id(workOrderId)}/update`, 'POST', { status, note }),
  photonWebhook: (payload: unknown) => request<{ ok: boolean }>('/webhooks/photon', 'POST', payload),
  messages: (party_id?: string, signal?: AbortSignal) => request<Model<'Message'>[]>(`/messages${query({ party_id })}`, 'GET', undefined, signal),
  messagingStatus: (signal?: AbortSignal) => request<Model<'MessagingStatus'>>('/messaging/status', 'GET', undefined, signal),
  simulateMessage: (payload: SimulatedMessage) => request<Model<'Message'>>('/demo/simulate-message', 'POST', payload),
  resources: (city?: string, signal?: AbortSignal) => request<Model<'Resource'>[]>(`/resources${query({ city })}`, 'GET', undefined, signal),
  referrals: (signal?: AbortSignal) => request<Model<'Referral'>[]>('/referrals', 'GET', undefined, signal),
  generateReport: (kind: Model<'ReportKind'>, building_id?: string) => request<Model<'Report'>>('/reports', 'POST', { kind, building_id }),
  reports: (signal?: AbortSignal) => request<Model<'Report'>[]>('/reports', 'GET', undefined, signal),
  reportHtmlUrl: (reportId: string) => `/api/reports/${id(reportId)}/html`,
  reportHtml: async (reportId: string, signal?: AbortSignal) => { const r = await fetch(`/api/reports/${id(reportId)}/html`, { signal }); if (!r.ok) throw new ApiError(r.status, r.statusText); return r.text(); },
};
