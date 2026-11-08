import type { Model } from "./api";

type Exposure = Model<"Exposure">;
type Plan = Model<"Plan">;

export function whatsWrong(exposure: Exposure | undefined): string {
  if (!exposure) return "Damage figures are still loading.";
  const parts: string[] = [];
  if (exposure.flood_depth_ft >= 0.5) parts.push(`${exposure.flood_depth_ft.toFixed(1)} ft of water`);
  if (exposure.wind_mph >= 40) parts.push(`${Math.round(exposure.wind_mph)} mph wind`);
  if (exposure.ice_in >= 0.1) parts.push(`${exposure.ice_in.toFixed(1)} in of ice`);
  if (exposure.temp_f != null && exposure.temp_f <= 32) parts.push(`${Math.round(exposure.temp_f)}°F`);
  if (exposure.grid_down) parts.push("the power is out");
  if (!parts.length) return "No damage expected here.";
  const sentence = parts.join(", ");
  return `${sentence.charAt(0).toUpperCase()}${sentence.slice(1)}.`;
}

export function crewVerb(exposure: Exposure | undefined): string {
  if (!exposure) return "Send the crew";
  if (exposure.flood_depth_ft >= 0.5) return "Send the flood crew";
  if (exposure.grid_down) return "Send the power crew";
  if (exposure.ice_in >= 0.1 || (exposure.temp_f != null && exposure.temp_f <= 32)) return "Send the cold-weather crew";
  if (exposure.wind_mph >= 50) return "Send the wind crew";
  return "Send the crew";
}

export function jobLine(plan: Plan | undefined): string {
  const titles = (plan?.actions ?? []).map((action) => action.title).filter(Boolean);
  if (!titles.length) return "No job is waiting.";
  if (titles.length === 1) return titles[0];
  return `${titles[0]}, plus ${titles.length - 1} more`;
}

export function taskName(code: string): string {
  return code.toLowerCase().replaceAll("_", " ");
}

export const CREW_STATUS: Record<string, string> = {
  created: "Queued",
  sent: "Sent to the crew",
  accepted: "Crew started",
  blocked: "Crew is stuck",
  done: "Done",
};
