import { useState } from 'react';
import type { Model } from '../../../../shared/api';
import { money, hours } from '../../../../shared/format';
import { useApprovePlan, useBuildings, useFixFirst, usePlans } from '../../../../shared/queries';
import { useUIStore } from '../../../../shared/ui-store';
import { Badge, Button, Card } from '../../../../shared/ui';
import './actions.css';
import EmergencyNotice from './EmergencyNotice';

function RankedPlan({ item }: { item: Model<'FixFirstItem'> }) {
  const approve = useApprovePlan();
  const { selectBuilding } = useUIStore();
  const [notice, setNotice] = useState('');
  return <Card className="response-card">
    <div className="response-heading"><Badge>#{item.rank}</Badge><Badge>{item.hours_left < 0 ? 'Deadline passed' : item.hours_left === 0 ? 'Act now' : `Act in ${item.hours_left}h`}</Badge></div>
    <button className="response-building" onClick={() => selectBuilding(item.building_id)}>{item.building_name}</button>
    <h3>{item.title}</h3><p>{item.why}</p>
    <dl className="panel-facts"><div><dt>Cost</dt><dd>{money(item.cost_cents)}</dd></div><div><dt>Saves</dt><dd>{money(item.avoided_cents)}</dd></div><div><dt>ROI</dt><dd>{item.roi.toFixed(1)}×</dd></div><div><dt>Act by impact hour</dt><dd>{hours(item.act_by_hour)}</dd></div></dl>
    <Button disabled={approve.isPending || approve.isSuccess || item.hours_left < 0} onClick={() => {
      setNotice('Approving plan…');
      approve.mutate({ id: item.plan_id, by: 'MGR-01' }, {
        onSuccess: () => setNotice('Plan approved. Check Work Orders for dispatch and completion.'),
        onError: () => setNotice('Approval failed. Refresh the list and retry; the deadline or plan may have changed.'),
      });
    }}>{approve.isPending ? 'Approving…' : approve.isSuccess ? 'Approved' : 'Approve plan'}</Button>
    {notice && <p role={approve.isError ? 'alert' : 'status'}>{notice}</p>}
  </Card>;
}

function RankedList({ community = false }: { community?: boolean }) {
  const query = useFixFirst(100, community);
  if (query.isError) return <div role="alert"><p>Plans are unavailable.</p><Button variant="outline" onClick={() => void query.refetch()}>Retry plans</Button></div>;
  if (query.isPending) return <p role="status">Loading response plans…</p>;
  if (!query.data.length) return <p className="panel-empty">{community ? 'No community actions available at this step.' : 'No plans needed at this step: nothing actionable is currently proposed.'}</p>;
  return <>{query.data.map(item => <RankedPlan key={item.plan_id} item={item} />)}</>;
}

export default function FixFirst() {
  const missed = usePlans({ status: 'missed' });
  const buildings = useBuildings();
  const { selectBuilding, setPanelView } = useUIStore();
  return <div className="response-view"><h2>Fix-First</h2>
    <p className="panel-caption">Prioritized by deadline and money saved per dollar. Countdown follows the scenario timeline.</p>
    <Button variant="outline" onClick={() => setPanelView('workorders')}>View Work Orders</Button>
    <EmergencyNotice />
    <RankedList />
    <h3 className="section-title">Community actions</h3><RankedList community />
    <h3 className="section-title">Missed opportunities</h3>
    {missed.isError ? <p role="alert">Missed plans are unavailable.</p> : missed.isPending ? <p role="status">Loading missed plans…</p> : !missed.data.length ? <p className="panel-empty">No missed plans at this step.</p> : missed.data.map(plan => <Card key={plan.id} className="response-card missed-plan">
      <Badge>Missed</Badge><button className="response-building" onClick={() => selectBuilding(plan.building_id)}>{buildings.data?.find(b => b.id === plan.building_id)?.name ?? plan.building_id}</button>
      <h3>{plan.actions?.map(a => a.title).join(' + ') || 'Response plan'}</h3>
      <p>Would have saved <strong>{money(plan.avoided_cents)}</strong></p><p className="panel-caption">Deadline: {hours(plan.act_by_hour)} relative to impact. Cost: {money(plan.cost_cents)}.</p>
    </Card>)}
    <p className="panel-caption">Approval records modeled mitigation intent. Work-order updates confirm execution.</p>
  </div>;
}
