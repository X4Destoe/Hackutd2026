import { useState } from "react";
import { ArrowRight, CheckCircle2, ListChecks } from "lucide-react";
import {
  useApprovePlan,
  useBuildings,
  useDemoState,
  useImpactFor,
  usePlans,
  useWorkOrders,
} from "../../shared/queries";
import { useUIStore } from "../../shared/ui-store";
import { hours, money } from "../../shared/format";
import { crewVerb, jobLine, taskName, whatsWrong, CREW_STATUS } from "../../shared/plain";
import { Button } from "../../shared/ui";
export default function ResponseCard() {
  const { selectedBuildingId } = useUIStore();
  return selectedBuildingId ? (
    <BuildingResponse key={selectedBuildingId} id={selectedBuildingId} />
  ) : null;
}
function BuildingResponse({ id }: { id: string }) {
  const { setPanelView } = useUIStore();
  const buildings = useBuildings();
  const impact = useImpactFor(id);
  const plans = usePlans({ building_id: id });
  const orders = useWorkOrders(id);
  const state = useDemoState();
  const approve = useApprovePlan();
  const [notice, setNotice] = useState("");
  const building = buildings.data?.find((b) => b.id === id);
  const plan =
    plans.data?.find((p) => p.status === "proposed") ??
    plans.data?.find((p) =>
      ["approved", "executing", "done"].includes(p.status),
    );
  const committed = Boolean(plan && plan.status !== "proposed");
  const left =
    plan && state.data ? plan.act_by_hour - state.data.step_hour : undefined;
  if (!building) return null;
  return (
    <section
      className="storm-response-card"
      aria-label="Building response actions"
    >
      <div className="response-eyebrow">
        <ListChecks size={14} />
        <span>{building.tenants?.length ? `${building.tenants.length} tenants` : "This building"}</span>
        {committed && <CheckCircle2 size={15} />}
      </div>
      <h2>{building.name}</h2>
      <p className="response-exposure">
        {impact.data ? whatsWrong(impact.data.exposure) : "Checking damage…"}{" "}
        <strong>
          {impact.data
            ? money(impact.data.money.net_exposure_cents)
            : ""}
        </strong>
      </p>
      {plan ? (
        <>
          <h3>{jobLine(plan)}</h3>
          <div className="response-economics">
            <div>
              <span>Cost</span>
              <strong>{money(plan.cost_cents)}</strong>
            </div>
            <div>
              <span>Saves</span>
              <strong>{money(plan.avoided_cents)}</strong>
            </div>
            <div>
              <span>ROI</span>
              <strong>{plan.roi.toFixed(1)}×</strong>
            </div>
          </div>
          {!committed && (
            <p className="response-deadline">
              {left != null && left > 0
                ? `Act within ${left} hours`
                : "Act now"}{" "}
              · deadline {hours(plan.act_by_hour)}
            </p>
          )}
          {committed ? (
            <div className="response-progress">
              <strong>
                {plan.status === "done" ? "Crew finished" : "Crew is on the way"}
              </strong>
              {orders.data?.length ? (
                <ul>
                  {orders.data.map((order) => (
                    <li key={order.id}>
                      <span>{taskName(order.action_code)}</span>
                      <b>{CREW_STATUS[order.status] ?? order.status}</b>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>{orders.isError ? "Tasks are unavailable." : "Tasks are on the way."}</p>
              )}
            </div>
          ) : (
            <Button
              disabled={approve.isPending || approve.isSuccess}
              onClick={() =>
                approve.mutate(
                  { id: plan.id, by: "MGR-01" },
                  {
                    onSuccess: () => setNotice("Crew is on the way."),
                    onError: () => setNotice("Could not send the crew. Try again."),
                  },
                )
              }
            >
              {approve.isPending ? "Sending…" : crewVerb(impact.data?.exposure)}
              <ArrowRight size={15} />
            </Button>
          )}
        </>
      ) : (
        <p className="response-unavailable">
          {plans.isPending
            ? "Looking for a job…"
            : plans.isError
              ? "Jobs are unavailable right now."
              : "Nothing to send for this building right now."}
        </p>
      )}
      {notice && (
        <p role="status" className="response-notice">
          {notice}
        </p>
      )}
      <button
        className="response-details"
        onClick={() => setPanelView("building")}
      >
        Who's here and the damage <ArrowRight size={13} />
      </button>
    </section>
  );
}
