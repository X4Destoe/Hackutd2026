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

export type SceneKind = "flood" | "power" | "cold" | "wind";

export type Scene = { src: string; caption: string; kind: SceneKind };

const CREW_PHOTOS: Record<SceneKind, string> = {
  flood: "/assets/crews/flood-crew.jpg",
  power: "/assets/crews/power-crew.jpg",
  cold: "/assets/crews/cold-crew.jpg",
  wind: "/assets/crews/wind-crew.jpg",
};

/** At most two pictures: the main problem, plus a power-out crew when the lights are out. */
export function crewPhotos(
  exposure: Exposure | undefined,
  orders?: { photo_urls?: string[] }[],
): Scene[] {
  const photos: Scene[] = [];
  if (exposure) {
    const cold = exposure.ice_in >= 0.1 || (exposure.temp_f != null && exposure.temp_f <= 32);
    if (exposure.flood_depth_ft >= 0.5) photos.push({ src: CREW_PHOTOS.flood, caption: "Flood crew", kind: "flood" });
    if (exposure.grid_down) photos.push({ src: CREW_PHOTOS.power, caption: "Power is out", kind: "power" });
    if (cold && photos.length < 2) photos.push({ src: CREW_PHOTOS.cold, caption: "Cold crew", kind: "cold" });
    if (exposure.wind_mph >= 50 && photos.length < 2) photos.push({ src: CREW_PHOTOS.wind, caption: "Wind crew", kind: "wind" });
  }
  const uploaded = orders?.flatMap((order) => order.photo_urls ?? []).filter(Boolean).at(-1);
  if (uploaded && photos.length) photos[0] = { ...photos[0], src: uploaded };
  else if (uploaded) photos.push({ src: uploaded, caption: "From the crew", kind: "flood" });
  return photos.slice(0, 2);
}

/** Pictures for a building. A site with no dollar damage only keeps a power-out photo. */
export function shownPhotos(
  exposure: Exposure | undefined,
  risk: string | undefined,
  orders?: { photo_urls?: string[] }[],
): Scene[] {
  const photos = crewPhotos(exposure, orders);
  if (risk === "none") return photos.filter((photo) => photo.kind === "power");
  return photos;
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
