import { useState } from "react";
import type { Model } from "../../../../shared/api";
import { useApprovePlan, useBuildings, useDemoState, usePlans, useResources, useWorkOrders } from "../../../../shared/queries";
import { useUIStore } from "../../../../shared/ui-store";
import { money, hours } from "../../../../shared/format";
import { Badge, Button } from "../../../../shared/ui";

function Activation({ building, plan, site, orders, unavailable, live, hour }: {
  building: Model<"Building">; plan: Model<"Plan">; site?: Model<"Resource">;
  orders: Model<"WorkOrder">[]; unavailable: boolean; live: boolean; hour?: number;
}) {
  const approve = useApprovePlan();
  const { selectBuilding, setPanelView } = useUIStore();
  const [notice, setNotice] = useState("");
  const proposed = plan.status === "proposed";
  const expired = hour !== undefined && hour > plan.act_by_hour;
  const tasks = orders.filter(order => order.plan_id === plan.id);
  return <article className="community-card help-activation" aria-label={`Help-site activation for ${building.name}`}>
    <div className="community-card-heading"><h3>{building.name}</h3><Badge>{site ? site.status : proposed ? "Available to propose" : "Registration unconfirmed"}</Badge></div>
    <p>{building.address}</p>
    <dl className="panel-facts">
      <div><dt>{site ? "Places available" : "Proposed capacity"}</dt><dd>{site ? Math.max(0, site.capacity - site.used) : building.host_capacity} people</dd></div>
      <div><dt>Setup cost</dt><dd>{money(plan.cost_cents)}</dd></div>
      <div><dt>Act by</dt><dd>{hours(plan.act_by_hour)} relative to impact</dd></div>
    </dl>
    {proposed && !site && <>
      <p>Approval registers this building with the help-routing service and sends a setup task to the on-site engineer.</p>
      <Button disabled={approve.isPending || approve.isSuccess || unavailable || live || expired || hour === undefined}
        onClick={() => approve.mutate({ id: plan.id, by: "MGR-01" }, {
          onSuccess: () => setNotice("Approval recorded. Checking site registration and task delivery…"),
          onError: () => setNotice("Activation could not be confirmed. Refresh the records before retrying."),
        })}> {approve.isPending ? "Activating…" : "Approve help-site activation"}</Button>
    </>}
    {live && <p className="attention-label">Live activation is unavailable until hazard and power checks are verified.</p>}
    {expired && proposed && <p className="attention-label">The activation deadline has passed.</p>}
    {unavailable && <p role="alert">Registration or task records are unavailable. Activation is disabled.</p>}
    {site && <p className={site.status === "unsafe" || site.status === "closed" ? "attention-label" : ""}>
      {site.status === "open" ? "Registered for routing" : `Registered · ${site.status}`} · {site.capacity} total places.
      {site.status !== "open" && " This site is not accepting new referrals."}
    </p>}
    {!proposed && !site && <p className="attention-label">Approval is recorded, but no registered site is confirmed. Follow up before directing residents here.</p>}
    {tasks.map(task => <div key={task.id} className={`activation-task ${task.status === "blocked" ? "needs-attention" : ""}`}>
      <strong>{task.id} · {task.status}</strong><span>Engineer {task.party_id}</span>
      {!!task.updates?.length && <p>{task.updates[task.updates.length - 1]}</p>}
    </div>)}
    {!!tasks.length && <Button variant="outline" onClick={() => { selectBuilding(building.id); setPanelView("workorders"); }}>View setup tasks</Button>}
    {notice && <p role={approve.isError ? "alert" : "status"}>{notice}</p>}
  </article>;
}

export default function HelpSiteActivation({ city }: { city?: string }) {
  const plans = usePlans();
  const buildings = useBuildings();
  const resources = useResources(city);
  const orders = useWorkOrders();
  const state = useDemoState();
  const candidates = (plans.data ?? []).flatMap(plan => {
    const building = buildings.data?.find(b => b.id === plan.building_id && b.city === city);
    return building && plan.actions?.some(action => action.code === "OFFER_HELP_SITE") &&
      ["proposed", "approved", "executing", "done"].includes(plan.status) ? [{ plan, building }] : [];
  });
  return <section className="help-activation-section" aria-label="CBRE community activation">
    <h3 className="section-title">Activate a CBRE help site</h3>
    <p className="panel-caption">Use portfolio space to help residents. Eligibility comes from the scenario model; site status and capacity come from the response service.</p>
    <p className="activation-channel">{state.data?.messaging_mode === "sim" ? "Simulator · setup texts stay in the demo inbox" : state.data?.messaging_mode === "photon" ? "Photon mode · verify delivery in setup tasks" : "Messaging channel unavailable"}</p>
    {plans.isError || buildings.isError ? <div role="alert"><p>Activation options are unavailable.</p><Button variant="outline" onClick={() => { void plans.refetch(); void buildings.refetch(); }}>Retry activation options</Button></div>
      : plans.isPending || buildings.isPending ? <p role="status">Checking eligible buildings…</p>
      : !candidates.length ? <p className="panel-empty">No eligible building activation plans at this step. Existing help sites remain listed above.</p>
      : candidates.map(({ plan, building }) => <Activation key={plan.id} plan={plan} building={building}
        site={resources.data?.find(site => site.building_id === building.id && site.type === "cbre_help_site")}
        orders={orders.data ?? []} unavailable={resources.isError || resources.isPending || orders.isError || orders.isPending || state.isError}
        live={state.data?.scenario_id.startsWith("live") ?? false} hour={state.data?.step_hour} />)}
  </section>;
}
