import { useState } from "react";
import {
  useApprovePlan,
  useBuildings,
  useGenerateReport,
  useImpactFor,
  usePlans,
  useWorkOrders,
} from "../../../shared/queries";
import { useUIStore } from "../../../shared/ui-store";
import { money, riskColor } from "../../../shared/format";
import { crewVerb, jobLine, taskName, whatsWrong, CREW_STATUS } from "../../../shared/plain";
import { Badge, Button } from "../../../shared/ui";
import PlanCard from "./PlanCard";
export default function BuildingDetail() {
  const { selectedBuildingId, setPanelView } = useUIStore();
  const id = selectedBuildingId ?? undefined;
  const buildings = useBuildings();
  const impact = useImpactFor(id);
  const plans = usePlans({ building_id: id });
  const orders = useWorkOrders(id);
  const report = useGenerateReport();
  const approve = useApprovePlan();
  const [sent, setSent] = useState("");
  const b = buildings.data?.find((b) => b.id === id);
  const i = impact.data;
  if (!id)
    return <p className="panel-empty">Select a building to see its impact.</p>;
  if (!b)
    return (
      <p role="status">
        {buildings.isError ? "Building unavailable." : "Loading building…"}
      </p>
    );
  const waterfall: [string, number, boolean][] = i
    ? [
        ["Property damage", i.money.property_damage_cents, false],
        ["Rent abatement", i.money.rent_abatement_cents, false],
        ["Tenant SLA", i.money.sla_penalty_cents, false],
        ["Operations", i.money.operations_cents, false],
        ["Insurance recovery", i.money.insurance_recovery_cents, true],
        ["Net exposure", i.money.net_exposure_cents, false],
      ]
    : [];
  const max = Math.max(1, ...waterfall.map(([, v]) => Math.abs(v)));
  const proposed = plans.data?.find((plan) => plan.status === "proposed");
  const people = b.tenants ?? [];
  return (
    <>
      <Button variant="ghost" onClick={() => setPanelView("buildings")}>
        All buildings
      </Button>
      <h2>{b.name}</h2>
      <p className="panel-caption">
        {b.city} · {b.address}
      </p>
      {i && (
        <Badge
          style={{
            background: riskColor(i.risk),
            color: i.risk === "moderate" || i.risk === "low" ? "#20342b" : "#fff",
          }}
        >
          {i.risk === "none" ? "No damage" : `${i.risk} damage`}
        </Badge>
      )}
      <h3 className="section-title">Who's here</h3>
      {people.length ? (
        <ul className="people-list">
          {people.map((tenant) => (
            <li key={tenant.id}>
              {tenant.name}
              {tenant.critical_ops ? " · needs the lights on" : ""}
            </li>
          ))}
        </ul>
      ) : (
        <p className="panel-empty">No tenants on file.</p>
      )}
      <h3 className="section-title">Damage</h3>
      {impact.isPending ? (
        <p role="status">Checking damage…</p>
      ) : impact.isError ? (
        <p className="panel-empty">Damage figures are unavailable.</p>
      ) : (
        i && (
          <>
            <p className="damage-lead">{whatsWrong(i.exposure)}</p>
            <p className="damage-money">
              Left after insurance <strong>{money(i.money.net_exposure_cents)}</strong>
            </p>
          </>
        )
      )}
      <h3 className="section-title">Crew</h3>
      {proposed ? (
        <>
          <p>{jobLine(proposed)}. Cost {money(proposed.cost_cents)}. Avoids about {money(proposed.avoided_cents)}.</p>
          <Button
            disabled={approve.isPending || approve.isSuccess}
            onClick={() =>
              approve.mutate(
                { id: proposed.id, by: "MGR-01" },
                {
                  onSuccess: () => setSent("Crew is on the way. Their tasks are in Work orders."),
                  onError: () => setSent("Could not send the crew. Try again."),
                },
              )
            }
          >
            {approve.isPending ? "Sending…" : crewVerb(i?.exposure)}
          </Button>
        </>
      ) : plans.isPending ? (
        <p role="status">Looking for a job to send…</p>
      ) : orders.data?.length ? (
        <p>The crew already has this building.</p>
      ) : (
        <p className="panel-empty">Nothing to send for this building right now.</p>
      )}
      {sent && <p role="status">{sent}</p>}
      {!!orders.data?.length && (
        <ul className="people-list">
          {orders.data.map((order) => (
            <li key={order.id}>
              {CREW_STATUS[order.status] ?? order.status} · {taskName(order.action_code)}
            </li>
          ))}
        </ul>
      )}
      <details className="more-detail">
        <summary>More detail</summary>
      <h3 className="section-title">Where the numbers come from</h3>
      <div className="source-chips">
        {(b.data_sources ?? []).map((source) => (
          <Badge key={source}>{source.replaceAll("_", " ")}</Badge>
        ))}
      </div>
      {impact.isPending ? (
        <p role="status">Loading impact…</p>
      ) : impact.isError ? (
        <p className="panel-empty">
          Financial impact is unavailable for this building.
        </p>
      ) : (
        i && (
          <>
            <h3 className="section-title">Hazard and power</h3>
            <dl className="panel-facts">
              <div>
                <dt>Flood / surge depth</dt>
                <dd>{i.exposure.flood_depth_ft.toFixed(1)} ft</dd>
              </div>
              <div>
                <dt>Wind</dt>
                <dd>{i.exposure.wind_mph.toFixed(0)} mph</dd>
              </div>
              <div>
                <dt>Ice</dt>
                <dd>{i.exposure.ice_in.toFixed(2)} in</dd>
              </div>
              <div>
                <dt>Temperature</dt>
                <dd>
                  {i.exposure.temp_f == null
                    ? "Not applicable"
                    : `${i.exposure.temp_f} °F`}
                </dd>
              </div>
              <div>
                <dt>Grid</dt>
                <dd>{i.exposure.grid_down ? "Down" : "Available"}</dd>
              </div>
              <div>
                <dt>Outage duration</dt>
                <dd>{i.exposure.power_out_hours} h</dd>
              </div>
              <div>
                <dt>Generator remaining</dt>
                <dd>
                  {i.exposure.generator_hours_left == null
                    ? "Not running"
                    : `${i.exposure.generator_hours_left} h`}
                </dd>
              </div>
            </dl>
            <h3 className="section-title">Why this building</h3>
            <ol className="cause-chain">
              {(i.exposure.cause_chain ?? []).map((cause, n) => (
                <li key={n}>{cause}</li>
              ))}
            </ol>
            <ul className="driver-list">
              {(i.drivers ?? []).map((driver, n) => (
                <li key={n}>{driver}</li>
              ))}
            </ul>
            <h3 className="section-title">Money waterfall</h3>
            <div className="waterfall">
              {waterfall.map(([label, value, credit]) => (
                <div key={label} className={credit ? "waterfall-credit" : ""}>
                  <div>
                    <span>{label}</span>
                    <strong>
                      {credit ? "−" : ""}
                      {money(value)}
                    </strong>
                  </div>
                  <span className="waterfall-track">
                    <span
                      style={{ width: `${(Math.abs(value) / max) * 100}%` }}
                    />
                  </span>
                </div>
              ))}
            </div>
            <p className="panel-caption">
              Estimated downtime: {i.money.downtime_days.toFixed(1)} days
            </p>
          </>
        )
      )}
      <h3 className="section-title">Response plans</h3>
      {plans.isPending ? (
        <p role="status">Loading plans…</p>
      ) : plans.isError ? (
        <p className="panel-empty">Response plans are unavailable.</p>
      ) : plans.data.length ? (
        plans.data.map((plan) => <PlanCard key={plan.id} plan={plan} />)
      ) : (
        <p className="panel-empty">No plans needed at this step.</p>
      )}
      <h3 className="section-title">Tenants</h3>
      <div className="tenant-table">
        <table>
          <thead>
            <tr>
              <th>Tenant</th>
              <th>Area</th>
              <th>Rent / day</th>
            </tr>
          </thead>
          <tbody>
            {(b.tenants ?? []).map((t) => (
              <tr key={t.id}>
                <td>
                  {t.name}
                  {t.critical_ops && <small>Critical operations</small>}
                </td>
                <td>{t.sqft.toLocaleString()} sq ft</td>
                <td>{money(t.rent_per_day_cents)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3 className="section-title">Work orders</h3>
      {orders.data?.length ? (
        orders.data.map((order) => (
          <div className="order-summary" key={order.id}>
            <Badge>{order.status}</Badge>
            <p>{order.text}</p>
            <small>{order.party_id}</small>
          </div>
        ))
      ) : (
        <p className="panel-empty">
          {orders.isError
            ? "Work orders are unavailable."
            : orders.isPending
              ? "Loading work orders…"
              : "No work orders for this building."}
        </p>
      )}
      <Button
        variant="outline"
        disabled={report.isPending}
        onClick={() =>
          report.mutate({ kind: "tenant_notice", building_id: b.id })
        }
      >
        Text the tenants
      </Button>
      {report.isSuccess && (
        <p role="status">Notice is ready. Open Reports to read it.</p>
      )}
      {report.isError && <p role="alert">Could not write the notice.</p>}
      </details>
    </>
  );
}
