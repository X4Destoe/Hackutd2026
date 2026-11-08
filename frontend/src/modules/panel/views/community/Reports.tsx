import { useEffect, useState } from "react";
import { api } from "../../../../shared/api";
import {
  useBuildings,
  useGenerateReport,
  useReports,
  useSummary,
} from "../../../../shared/queries";
import { useUIStore } from "../../../../shared/ui-store";
import { Button } from "../../../../shared/ui";
export default function Reports() {
  const reports = useReports();
  const buildings = useBuildings();
  const generate = useGenerateReport();
  const summary = useSummary();
  const unknown = summary.data?.data_quality === "unknown";
  const { selectedBuildingId } = useUIStore();
  const [building, setBuilding] = useState(selectedBuildingId ?? "");
  useEffect(() => {
    if (selectedBuildingId) setBuilding(selectedBuildingId);
  }, [selectedBuildingId]);
  return (
    <div className="community-view">
      <h2>Reports</h2>
      <p className="panel-caption">
        Create a report, review it, then print or share it.
      </p>
      {unknown && <p role="status" className="attention-label">Live financial inputs are unknown. Report generation is unavailable until current source data is confirmed.</p>}
      <div className="report-controls">
        <Button
          disabled={generate.isPending || unknown}
          onClick={() => generate.mutate({ kind: "executive_summary" })}
        >
          Generate executive summary
        </Button>
        <label>
          Tenant notice building
          <select
            aria-label="Tenant notice building"
            value={building}
            onChange={(e) => setBuilding(e.target.value)}
          >
            <option value="">Choose a building</option>
            {buildings.data?.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        </label>
        <Button
          variant="outline"
          disabled={!building || generate.isPending || unknown}
          onClick={() =>
            generate.mutate({ kind: "tenant_notice", building_id: building })
          }
        >
          Generate tenant notice
        </Button>
      </div>
      {generate.isPending && <p role="status">Generating report…</p>}
      {generate.isError && (
        <p role="alert">Could not generate the report. Please retry.</p>
      )}
      {generate.isSuccess && (
        <p role="status">
          Report generated. Review the printable version below.
        </p>
      )}
      <h3 className="section-title">Generated reports</h3>
      {reports.isPending ? (
        <p role="status">Loading reports…</p>
      ) : reports.isError ? (
        <div role="alert" className="panel-empty">Reports are unavailable. <Button variant="outline" disabled={reports.isFetching} onClick={() => void reports.refetch()}>Retry reports</Button></div>
      ) : reports.data.length === 0 ? (
        <p className="panel-empty">No reports generated yet.</p>
      ) : (
        <ul className="community-list">
          {reports.data.map((report) => (
            <li key={report.id} className="community-card">
              <h3>{report.title}</h3>
              <p>
                {report.kind.replaceAll("_", " ")} ·{" "}
                {new Date(report.created_wall).toLocaleString()}
              </p>
              <a
                href={api.reportHtmlUrl(report.id)}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open printable report
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
