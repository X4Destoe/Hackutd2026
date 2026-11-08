import TermHelp from "../../../shared/TermHelp";
import { useState } from "react";
import type { Model } from "../../../shared/api";
import { useApprovePlan, useRejectPlan } from "../../../shared/queries";
import { money, hours } from "../../../shared/format";
import { Button, Card } from "../../../shared/ui";
export default function PlanCard({ plan }: { plan: Model<"Plan"> }) {
  const approve = useApprovePlan();
  const reject = useRejectPlan();
  const [notice, setNotice] = useState("");
  const pending = approve.isPending || reject.isPending;
  const act = (accepted: boolean) => {
    setNotice(accepted ? "Approving plan…" : "Rejecting plan…");
    const mutation = accepted ? approve : reject;
    mutation.mutate(
      { id: plan.id, by: "MGR-01" },
      {
        onSuccess: () =>
          setNotice(
            accepted
              ? "Plan approved. Response tasks are being prepared."
              : "Plan rejected.",
          ),
        onError: () => setNotice("Could not update this plan. Please retry."),
      },
    );
  };
  return (
    <Card
      className={`plan-card ${plan.status === "missed" ? "missed-plan" : ""}`}
    >
      <h3>
        {(plan.actions ?? []).map((a) => a.title).join(" + ") ||
          "Response plan"}
      </h3>
      <p>{plan.rationale}</p>
      <dl className="panel-facts">
        <div>
          <dt>Cost</dt>
          <dd>{money(plan.cost_cents)}</dd>
        </div>
        <div>
          <dt>
            <TermHelp term={plan.status === "missed" ? "Would have saved" : "Potential savings"} />
          </dt>
          <dd>{money(plan.avoided_cents)}</dd>
        </div>
        <div>
          <dt><TermHelp term="ROI" /></dt>
          <dd>{plan.roi.toFixed(1)}×</dd>
        </div>
        <div>
          <dt><TermHelp term="Act by" /></dt>
          <dd>{hours(plan.act_by_hour)}</dd>
        </div>
      </dl>
      <p className="panel-caption">Status: {plan.status}</p>
      {plan.status === "proposed" && (
        <div className="panel-actions">
          <Button
            disabled={pending || approve.isSuccess || reject.isSuccess}
            onClick={() => act(true)}
          >
            Approve plan
          </Button>
          <Button
            variant="outline"
            disabled={pending || approve.isSuccess || reject.isSuccess}
            onClick={() => act(false)}
          >
            Reject
          </Button>
        </div>
      )}
      {notice && (
        <p role="status" className="action-notice">
          {notice}
        </p>
      )}
    </Card>
  );
}
