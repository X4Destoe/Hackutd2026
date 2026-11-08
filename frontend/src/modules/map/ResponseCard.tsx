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
import { Button } from "../../shared/ui";
import WorkOrderControl from "./WorkOrderControl";
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
        <span>Decision → response</span>
        {committed && <CheckCircle2 size={15} />}
      </div>
      <h2>{building.name}</h2>
      <p className="response-exposure">
        Net exposure{" "}
        <strong>
          {impact.data
            ? money(impact.data.money.net_exposure_cents)
            : "Unavailable"}
        </strong>
      </p>
      {plan ? (
        <>
          <h3>
            {plan.actions?.map((a) => a.title).join(" + ") || "Response plan"}
          </h3>
          <div className="response-economics">
            <div>
              <span>Investment</span>
              <strong>{money(plan.cost_cents)}</strong>
            </div>
            <div>
              <span>
                {committed ? "Modeled avoided loss" : "Savings potential"}
              </span>
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
                {plan.status === "done"
                  ? "Response completed"
                  : plan.status === "executing"
                    ? "Execution in progress"
                    : "Plan approved"}
              </strong>
              {orders.data?.length ? (
                <div>
                  {orders.data.map((order) => (
                    <WorkOrderControl key={order.id} order={order} />
                  ))}
                </div>
              ) : (
                <p>
                  {orders.isError
                    ? "Dispatch status unavailable. Approval is recorded; task delivery is not confirmed."
                    : "Waiting for execution records. Approval is recorded; task delivery is not confirmed."}
                </p>
              )}
            </div>
          ) : (
            <Button
              disabled={approve.isPending || approve.isSuccess}
              onClick={() =>
                approve.mutate(
                  { id: plan.id, by: "MGR-01" },
                  {
                    onSuccess: () =>
                      setNotice("Plan approved. Checking execution status…"),
                    onError: () =>
                      setNotice(
                        "Approval failed. No success is assumed; please retry.",
                      ),
                  },
                )
              }
            >
              {approve.isPending ? "Approving…" : "Approve response plan"}
              <ArrowRight size={15} />
            </Button>
          )}
        </>
      ) : (
        <p className="response-unavailable">
          {plans.isPending
            ? "Finding response options…"
            : plans.isError
              ? "Response planning is unavailable. Review building exposure while the service reconnects."
              : "No proposed response plan for this step."}
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
        Inspect drivers and financial breakdown <ArrowRight size={13} />
      </button>
    </section>
  );
}
