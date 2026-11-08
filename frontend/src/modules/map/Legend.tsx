// Legend: $ risk colors + the active scenario's hazard ramp.
import { useDemoState, useScenarios } from '../../shared/queries';
import { riskColor, type RiskLevel } from '../../shared/format';

const RISKS: [RiskLevel, string][] = [['severe', '≥ $1M'], ['high', '$250k–1M'], ['moderate', '$50–250k'], ['low', '< $50k'], ['none', 'none']];
const WATER = [['#8ec5f2', '< 1 ft'], ['#4b9be6', '1–3 ft'], ['#1f6fc4', '3–6 ft'], ['#0d4a94', '6 ft +']];

export default function Legend() {
  const state = useDemoState();
  const meta = useScenarios().data?.find((s) => s.id === state.data?.scenario_id);
  const hazards = meta?.hazards ?? [];
  const wet = hazards.includes('flood') || hazards.includes('surge');
  return (
    <aside className="storm-legend" aria-label="Map legend">
      <div className="storm-legend-title" title="After insurance and approved actions">Estimated loss</div>
      {RISKS.map(([risk, text]) => (
        <div key={risk} className="storm-legend-row"><span style={{ background: riskColor(risk) }} />{risk[0].toUpperCase() + risk.slice(1)} <em>{text}</em></div>
      ))}
      <div className="storm-legend-row"><span style={{ background: '#64748b' }} />Unknown <em>Data unavailable</em></div>
      {wet && <>
        <div className="storm-legend-title">{hazards.includes('surge') ? 'Storm surge depth' : 'Flood depth'}</div>
        <div className="storm-legend-ramp">{WATER.map(([c, t]) => <span key={t} title={t} style={{ background: c }} />)}</div>
        <div className="storm-legend-scale"><em>&lt; 1 ft</em><em>6 ft +</em></div>
      </>}
      {hazards.includes('winter') && <div className="storm-legend-row"><span style={{ background: '#bcd6f2', borderColor: '#8fb8e0' }} />Snow and ice area</div>}
      <div className="storm-legend-row"><span className="dash" />Forecast (predicted)</div>
      <div className="storm-legend-row"><span className="dot" />Substation · red = down</div>
    </aside>
  );
}
