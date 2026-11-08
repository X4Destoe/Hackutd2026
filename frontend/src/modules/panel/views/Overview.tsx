import TermHelp from "../../../shared/TermHelp";
import { useFixFirst, usePlans, useSummary } from "../../../shared/queries";
import { useUIStore } from "../../../shared/ui-store";
import { money, hours } from "../../../shared/format";
import { Button, Card } from "../../../shared/ui";
import PlanCard from "./PlanCard";
export default function Overview() {
  const summary = useSummary();
  const first = useFixFirst(5);
  const plans = usePlans({ status: "missed" });
  const { selectBuilding } = useUIStore();
  return (
    <>
      <h2>Portfolio overview</h2>
      <p className="panel-caption">Estimated loss accounts for insurance and approved actions. Figures are modeled.</p>
      {summary.isPending ? (
        <p role="status">Loading portfolio impact…</p>
      ) : summary.isError ? (
        <p className="panel-empty">
          Portfolio impact is unavailable. Building records are still
          accessible.
        </p>
      ) : summary.data.data_quality === "unknown" ? <p role="status" className="panel-empty">Financial impact is unknown because live inputs are unavailable or stale. This does not mean zero loss or safe conditions.</p> : (
        <dl className="kpi-grid">
          {[
            ["Buildings at risk", String(summary.data.buildings_at_risk)],
            ["Gross loss", money(summary.data.gross_loss_cents)],
            ["Estimated loss", money(summary.data.net_exposure_cents)],
            ["Avoided", money(summary.data.avoided_cents)],
            ["Approved actions", String(summary.data.actions_approved)],
            [
              "Insurance recovery",
              summary.data.insurance_recovery_cents == null
                ? "—"
                : money(summary.data.insurance_recovery_cents),
            ],
          ].map(([label, value]) => (
            <div key={label}>
              <dt><TermHelp term={label} /></dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      )}
      <h3 className="section-title">Fix-First · top five</h3>
      {first.isPending ? (
        <p role="status">Loading priorities…</p>
      ) : first.isError ? (
        <p className="panel-empty">
          Response priorities are not available yet.
        </p>
      ) : first.data.length === 0 ? (
        <p className="panel-empty">
          No plans needed at this step: nothing is exposed yet.
        </p>
      ) : (
        first.data.map((item) => (
          <Card key={item.plan_id} className="priority-card">
            <span className="panel-caption">
              Priority {item.rank} · act by {hours(item.act_by_hour)}
            </span>
            <h3>{item.title}</h3>
            <p>{item.building_name}</p>
            <div className="priority-money">
              {money(item.cost_cents)} <span>cost · saves</span>{" "}
              {money(item.avoided_cents)} <span>({item.roi.toFixed(1)}×)</span>
            </div>
            <p>{item.why}</p>
            <Button
              variant="outline"
              onClick={() => selectBuilding(item.building_id)}
            >
              View {item.building_name}
            </Button>
          </Card>
        ))
      )}
      {plans.data && plans.data.length > 0 && (
        <>
          <h3 className="section-title">Missed opportunities</h3>
          {plans.data.map((plan) => (
            <PlanCard key={plan.id} plan={plan} />
          ))}
        </>
      )}
    </>
  );
}
