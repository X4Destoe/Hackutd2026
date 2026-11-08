import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { api, type Model, type PlanFilter, type SimulatedMessage } from './api';
// Prefix keys intentionally group all hours, filters and selected-building queries.
export const scenarioKeys = ['demoState', 'overlays', 'impact', 'summary', 'plans', 'fixFirst', 'resources', 'utilities', 'buildings', 'workOrders', 'referrals', 'messages', 'messagingStatus', 'reports'];
export function invalidateKeys(client: QueryClient, keys: readonly string[]) { return Promise.all(keys.map(key => client.invalidateQueries({ queryKey: [key] }))); }
export const useScenarios = () => useQuery({ queryKey: ['scenarios'], queryFn: ({ signal }) => api.scenarios(signal) });
export const useDemoState = () => useQuery({ queryKey: ['demoState'], queryFn: ({ signal }) => api.demoState(signal) });
export const useOverlays = (hour?: number) => useQuery({ queryKey: ['overlays', hour], queryFn: ({ signal }) => api.overlays(hour, signal) });
export const useBuildings = () => useQuery({ queryKey: ['buildings'], queryFn: ({ signal }) => api.buildings(signal) });
export const useUtilities = () => useQuery({ queryKey: ['utilities'], queryFn: ({ signal }) => api.utilities(signal) });
export const useImpact = (hour?: number) => useQuery({ queryKey: ['impact', hour], queryFn: ({ signal }) => api.impact(hour, signal) });
export const useImpactFor = (id?: string, hour?: number) => useQuery({ queryKey: ['impact', id, hour], queryFn: ({ signal }) => api.impactFor(id!, hour, signal), enabled: !!id });
export const useSummary = () => useQuery({ queryKey: ['summary'], queryFn: ({ signal }) => api.summary(signal) });
export const useCatalog = () => useQuery({ queryKey: ['catalog'], queryFn: ({ signal }) => api.catalog(signal) });
export const usePlans = (filter: PlanFilter = {}) => useQuery({ queryKey: ['plans', filter], queryFn: ({ signal }) => api.plans(filter, signal) });
export const useFixFirst = (limit = 10, community = false) => useQuery({ queryKey: ['fixFirst', limit, community], queryFn: ({ signal }) => api.fixFirst(limit, community, signal) });
export const useWorkOrders = (buildingId?: string) => useQuery({ queryKey: ['workOrders', buildingId], queryFn: ({ signal }) => api.workOrders(buildingId, signal) });
export const useResources = (city?: string) => useQuery({ queryKey: ['resources', city], queryFn: ({ signal }) => api.resources(city, signal) });
export const useReferrals = () => useQuery({ queryKey: ['referrals'], queryFn: ({ signal }) => api.referrals(signal) });
export const useReports = () => useQuery({ queryKey: ['reports'], queryFn: ({ signal }) => api.reports(signal) });
export const useMessages = (partyId?: string) => useQuery({ queryKey: ['messages', partyId], queryFn: ({ signal }) => api.messages(partyId, signal) });
export const useMessagingStatus = () => useQuery({ queryKey: ['messagingStatus'], queryFn: ({ signal }) => api.messagingStatus(signal) });
export function useLoadScenario() { const c = useQueryClient(); return useMutation({ mutationFn: api.loadScenario, onSuccess: () => invalidateKeys(c, scenarioKeys) }); }
export function useSetHour() { const c = useQueryClient(); return useMutation({ mutationFn: api.setHour, onSuccess: () => invalidateKeys(c, scenarioKeys) }); }
export function useReset() { const c = useQueryClient(); return useMutation({ mutationFn: api.reset, onSuccess: () => invalidateKeys(c, scenarioKeys) }); }
export function useApprovePlan() { const c = useQueryClient(); return useMutation({ mutationFn: ({ id, by }: { id: string; by: string }) => api.approvePlan(id, by), onSuccess: () => invalidateKeys(c, ['plans', 'fixFirst', 'summary', 'impact', 'workOrders', 'messages', 'resources']) }); }
export function useRejectPlan() { const c = useQueryClient(); return useMutation({ mutationFn: ({ id, by }: { id: string; by: string }) => api.rejectPlan(id, by), onSuccess: () => invalidateKeys(c, ['plans', 'fixFirst', 'summary']) }); }
export function useUpdateWorkOrder() { const c = useQueryClient(); return useMutation({ mutationFn: ({ id, status, note }: { id: string; status: Model<'WorkOrderStatus'>; note?: string }) => api.updateWorkOrder(id, status, note), onSuccess: () => invalidateKeys(c, ['workOrders', 'plans', 'impact', 'summary']) }); }
export function useGenerateReport() { const c = useQueryClient(); return useMutation({ mutationFn: ({ kind, building_id }: { kind: Model<'ReportKind'>; building_id?: string }) => api.generateReport(kind, building_id), onSuccess: () => invalidateKeys(c, ['reports']) }); }
export function useSimulateMessage() { const c = useQueryClient(); return useMutation({ mutationFn: (payload: SimulatedMessage) => api.simulateMessage(payload), onSuccess: () => invalidateKeys(c, ['messages', 'messagingStatus', 'workOrders', 'plans', 'resources', 'referrals', 'impact', 'summary']) }); }
