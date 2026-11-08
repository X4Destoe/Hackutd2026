import { useQuery } from "@tanstack/react-query";
import { api } from "../../shared/api";
import { useDemoState } from "../../shared/queries";

/** Hour alone is not a cache key: Harvey and Uri both have a −48h step. */
export function useMapImpact(hour?: number) {
  const scenarioId = useDemoState().data?.scenario_id;
  return useQuery({
    queryKey: ["impact", scenarioId, hour ?? "live"],
    queryFn: ({ signal }) => api.impact(hour, signal),
    enabled: Boolean(scenarioId),
  });
}

export function useMapOverlays(hour?: number) {
  const scenarioId = useDemoState().data?.scenario_id;
  return useQuery({
    queryKey: ["overlays", scenarioId, hour ?? "live"],
    queryFn: ({ signal }) => api.overlays(hour, signal),
    enabled: Boolean(scenarioId),
  });
}
