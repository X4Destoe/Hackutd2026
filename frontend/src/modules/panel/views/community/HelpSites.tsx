import { useResources, useReferrals } from "../../../../shared/queries";
import { Badge, Button, Progress } from "../../../../shared/ui";
import HelpSiteActivation from "./HelpSiteActivation";
export default function HelpSites({ city }: { city?: string }) {
  const sites = useResources(city);
  const referrals = useReferrals();
  const byId = new Map(sites.data?.map((site) => [site.id, site]));
  const ordered = [...(referrals.data ?? [])].sort(
    (a, b) =>
      Number(b.status === "unrouted" || b.needs?.includes("medical")) -
      Number(a.status === "unrouted" || a.needs?.includes("medical")),
  );
  return (
    <div className="community-view">
      <h2>Help Sites</h2>
      <p className="panel-caption">
        {city ?? "Current scenario"} · Capacity and safety from the response
        service. Demo locations and modeled availability; confirm actual conditions before travel.
      </p>
      {!!ordered.filter(r => r.status === "unrouted").length && <p className="attention-label" role="status">
        {ordered.filter(r => r.status === "unrouted").reduce((sum, r) => sum + r.people, 0)} people awaiting a placement. Coordinator follow-up required.
      </p>}
      {sites.isPending ? (
        <p role="status">Loading help sites…</p>
      ) : sites.isError ? (
        <p role="alert" className="panel-empty">
          Help sites are unavailable.
          <Button variant="outline" disabled={sites.isFetching} onClick={() => void sites.refetch()}>Retry help sites</Button>
        </p>
      ) : sites.data.length === 0 ? (
        <p className="panel-empty">
          No help sites are registered for this city.
        </p>
      ) : (
        <ul className="community-list">
          {sites.data.map((site) => (
            <li key={site.id} className={`community-card site-${site.status}`}>
              <div className="community-card-heading">
                <h3>{site.name}</h3>
                <Badge>
                  {site.status === "unsafe"
                    ? "Unsafe · do not route"
                    : site.status}
                </Badge>
              </div>
              <p>
                {site.type.replaceAll("_", " ")} · {site.address}
              </p>
              <p>{site.hours}</p>
              <Progress
                label={`${site.name} capacity used`}
                value={
                  site.capacity > 0
                    ? ((site.used ?? 0) / site.capacity) * 100
                    : 100
                }
              />
              <p className="community-meta">
                {Math.max(0, site.capacity - (site.used ?? 0))} of{" "}
                {site.capacity} places available
              </p>
              <div className="site-contact-actions">
              {site.status === "open" && site.capacity > (site.used ?? 0) ? (
                <a href={`https://www.google.com/maps/dir/?api=1&destination=${site.lat},${site.lon}`}
                  target="_blank" rel="noopener noreferrer" aria-label={`Directions to ${site.name} (opens in new tab)`}>
                  Open directions
                </a>
              ) : <span className="site-routing-unavailable">{site.status === "unsafe" ? "Directions withheld: modeled unsafe conditions" : site.status === "full" || site.used >= site.capacity ? "No places available for routing" : "Site is closed for routing"}</span>}
              {site.phone && (
                <a href={`tel:${site.phone.replace(/[^+\d]/g, "")}`}>
                  Call site
                </a>
              )}
              </div>
            </li>
          ))}
        </ul>
      )}
      <h3 className="section-title">Resident referrals</h3>
      {referrals.isPending ? (
        <p role="status">Loading referrals…</p>
      ) : referrals.isError ? (
        <div className="panel-empty" role="alert">Referral records are unavailable. <Button variant="outline" disabled={referrals.isFetching} onClick={() => void referrals.refetch()}>Retry referrals</Button></div>
      ) : ordered.length === 0 ? (
        <p className="panel-empty">No resident requests yet.</p>
      ) : (
        <ul className="community-list">
          {ordered.map((referral) => (
            <li
              className={`community-card ${referral.status === "unrouted" || referral.needs?.includes("medical") ? "needs-attention" : ""}`}
              key={referral.id}
            >
              <div className="community-card-heading">
                <strong>{referral.party_id}</strong>
                <Badge>
                  {referral.needs?.includes("medical")
                    ? "Urgent · medical"
                    : referral.status}
                </Badge>
              </div>
              <p>{referral.summary}</p>
              <p>
                {referral.people ?? 1} people ·{" "}
                {byId.get(referral.resource_id ?? "")?.name ??
                  (referral.resource_id
                    ? referral.resource_id
                    : "Awaiting coordinator")}
                {referral.distance_mi != null
                  ? ` · ${referral.distance_mi.toFixed(1)} mi`
                  : ""}
              </p>
              {referral.status === "unrouted" && (
                <p className="attention-label">
                  Coordinator follow-up required
                </p>
              )}
              {referral.history?.length ? (
                <ol>
                  {referral.history.map((entry, i) => (
                    <li key={i}>{entry}</li>
                  ))}
                </ol>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      <HelpSiteActivation city={city} />
    </div>
  );
}
