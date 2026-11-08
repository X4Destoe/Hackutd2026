import { useId, useState } from "react";
import { ArrowRight, CheckCircle2, ListChecks, Minus, Maximize2, X } from "lucide-react";
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
  const { setPanelView, setSelectedBuildingId } = useUIStore();
  const [minimized, setMinimized] = useState(false);
  const bodyId = useId();
  const close = () => {
    setSelectedBuildingId(null);
    setPanelView("overview");
    document.querySelector<HTMLButtonElement>(`[data-building-id="${CSS.escape(id)}"]`)?.focus();
  };
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
      className={`storm-response-card${minimized ? " is-minimized" : ""}`}
      onKeyDown={event => { if (event.key === "Escape") { event.stopPropagation(); close(); } }}
      aria-label="Building response actions"
    >
      <div className="response-card-header">
      <div className="response-card-title">
      <div className="response-eyebrow">
        <ListChecks size={14} />
        <span>Decision → response</span>
        {committed && <CheckCircle2 size={15} />}
      </div>
      <h2 title={building.name}>{building.name}</h2>
      </div>
      <div className="response-card-controls">
        <button type="button" aria-label={minimized ? "Restore building response card" : "Minimize building response card"}
          title={minimized ? "Restore" : "Minimize"} aria-expanded={!minimized} aria-controls={bodyId}
          onClick={() => setMinimized(value => !value)}>
          {minimized ? <Maximize2 size={16} /> : <Minus size={16} />}
        </button>
        <button type="button" aria-label="Close building response card" title="Close" onClick={close}><X size={17} /></button>
      </div>
      </div>
      <div className="response-card-body" id={bodyId} hidden={minimized}>
      <p className="response-exposure" title="After insurance and approved actions">
        Estimated loss{" "}
        <strong>
          {impact.data?.data_quality === "unknown" ? "Unknown" : impact.data
            ? money(impact.data.money.net_exposure_cents)
            : "Unavailable"}
        </strong>
      </p>
      {impact.data?.data_quality === "unknown" && <p className="response-unavailable">Live financial inputs are unavailable. This does not confirm zero loss or safe conditions.</p>}
      {impact.data?.data_quality === "live_proxy" && <p className="response-unavailable">Alert-based estimates; power conditions are unverified.</p>}
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
      </div>
    </section>
  );
}
