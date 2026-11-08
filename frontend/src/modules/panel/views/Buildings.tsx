import { useState } from "react";
import { useBuildings, useImpact } from "../../../shared/queries";
import { useUIStore } from "../../../shared/ui-store";
import { money, riskColor } from "../../../shared/format";
export default function Buildings({
  search,
  city,
}: {
  search: string;
  city?: string;
}) {
  const buildings = useBuildings();
  const impacts = useImpact();
  const { selectBuilding } = useUIStore();
  const [sort, setSort] = useState("exposure");
  const [localOnly, setLocalOnly] = useState(true);
  const impactById = new Map(impacts.data?.map((i) => [i.building_id, i]));
  const list = (buildings.data ?? [])
    .filter(
      (b) =>
        (!localOnly || !city || b.city === city) &&
        [b.name, b.city, ...(b.tenants ?? []).map((t) => t.name)].some((v) =>
          v.toLowerCase().includes(search.toLowerCase()),
        ),
    )
    .sort((a, b) =>
      sort === "name"
        ? a.name.localeCompare(b.name)
        : sort === "risk"
          ? ["none", "low", "moderate", "high", "severe"].indexOf(
              impactById.get(b.id)?.risk ?? "none",
            ) -
            ["none", "low", "moderate", "high", "severe"].indexOf(
              impactById.get(a.id)?.risk ?? "none",
            )
          : (impactById.get(b.id)?.money.net_exposure_cents ?? 0) -
            (impactById.get(a.id)?.money.net_exposure_cents ?? 0),
    );
  const max = Math.max(
    1,
    ...list.map((b) => impactById.get(b.id)?.money.net_exposure_cents ?? 0),
  );
  return (
    <>
      <h2>Buildings</h2>
      <label className="sort-row">
        Sort by{" "}
        <select value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="exposure">Estimated loss</option>
          <option value="name">Name</option>
          <option value="risk">Risk</option>
        </select>
      </label>
      <label className="panel-check">
        <input
          type="checkbox"
          checked={localOnly}
          onChange={(e) => setLocalOnly(e.target.checked)}
        />{" "}
        Only in this scenario
      </label>
      {buildings.isPending ? (
        <p role="status">Loading buildings…</p>
      ) : buildings.isError ? (
        <p role="alert">Building records could not be loaded.</p>
      ) : list.length === 0 ? (
        <p className="panel-empty">No matching buildings.</p>
      ) : (
        list.map((b) => {
          const impact = impactById.get(b.id);
          return (
            <button
              key={b.id}
              className="building-row"
              onClick={() => selectBuilding(b.id)}
            >
              <span className="building-row-title">
                <span
                  className="risk-square"
                  style={{ background: riskColor(impact?.risk ?? "none") }}
                />
                <strong>{b.name}</strong>
              </span>
              <span className="building-row-meta">
                {b.city}
                <b>
                  {impact
                    ? money(impact.money.net_exposure_cents)
                    : "Impact pending"}
                </b>
              </span>
              {impact && (
                <span className="exposure-bar">
                  <span
                    style={{
                      width: `${Math.max(0, (impact.money.net_exposure_cents / max) * 100)}%`,
                      background: riskColor(impact.risk),
                    }}
                  />
                </span>
              )}
            </button>
          );
        })
      )}
    </>
  );
}
