import { useQuery } from "@tanstack/react-query";
import { useDemoState } from "../../shared/queries";
import { Button } from "../../shared/ui";
import "./live.css";

type Feed = { as_of: string | null; stale: boolean; error: string | null };
type Status = { feeds: Record<string, Feed>; refreshing: boolean; alert_count: number; alerts_without_area: number; notes?: string[] };
const CITIES: Record<string, string> = { live_houston: "Houston", live_dallas: "Dallas", live_fort_myers: "Fort Myers" };
function fetched(feed?: Feed) {
  const stamp = feed?.as_of ? Date.parse(feed.as_of) : NaN;
  if (!Number.isFinite(stamp)) return { unknown: true, text: "Unknown · never fetched" };
  const stale = feed?.stale || Boolean(feed?.error) || Date.now() - stamp > 15 * 60 * 1000;
  return { unknown: stale, text: `${stale ? "Stale · " : ""}fetched ${new Date(stamp).toLocaleString()}` };
}

/** Fetch receipt time is not a hazard observation timestamp or a safety guarantee. */
export default function LiveStatus({ city }: { city?: string }) {
  const state = useDemoState();
  const active = state.data?.scenario_id.startsWith("live") ?? false;
  const cityName = city ?? CITIES[state.data?.scenario_id ?? ""];
  const status = useQuery({ queryKey: ["liveStatus"], enabled: active,
    queryFn: async (): Promise<Status> => {
      const response = await fetch("/api/live/status");
      if (!response.ok) throw new Error("Live status unavailable");
      return response.json();
    }, refetchInterval: 60_000 });
  if (!active) return null;
  const sources = [["alerts", "NWS alerts"], [`forecast:${cityName}`, "NWS forecast"], [`gauges:${cityName}`, "USGS gauges"]];
  const unknown = status.isError || !status.data || sources.some(([key]) => fetched(status.data.feeds?.[key]).unknown);
  return <section className={`storm-live-status ${unknown ? "live-unknown" : ""}`} aria-label="Live data quality" data-quality={unknown ? "unknown" : "available"}>
    <strong>Live inputs · modeled effects</strong>
    <p>{status.isPending ? "Checking sources…" : status.isError ? "Source status unavailable" : unknown ? "Some inputs are stale or unknown" : "Source fetches are current"}</p>
    <small>Power status unverified · screening only</small>
    <details><summary>Data sources and limits</summary>
      {status.isError ? <div role="alert"><p>Cannot verify source freshness.</p><Button variant="outline" onClick={() => void status.refetch()}>Retry live status</Button></div> :
        <ul>{sources.map(([key, label]) => { const feed = status.data?.feeds?.[key]; const value = fetched(feed);
          return <li key={key}><b>{label}</b><span>{value.text}</span>{feed?.error && <span>Fetch failed; previous data may remain cached.</span>}</li>;
        })}</ul>}
      {status.data && <p>{status.data.alert_count} alerts across monitored states; {status.data.alerts_without_area} without a drawable area.{status.data.refreshing && " Background refresh running."}</p>}
      <p>NWS alert areas do not provide flood depths. Modeled intensities are proxies. Gauge height is not water depth at a building.</p>
      <p>Times above record source fetches, not measurements. Sources are rechecked automatically; unknown conditions do not mean safe conditions.</p>
    </details>
  </section>;
}
