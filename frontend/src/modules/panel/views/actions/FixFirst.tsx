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
    <dl className="panel-facts"><div><dt>Cost</dt><dd>{money(item.cost_cents)}</dd></div><div><dt>Saves</dt><dd>{money(item.avoided_cents)}</dd></div><div><dt>Payback</dt><dd>{item.roi.toFixed(1)}×</dd></div><div><dt>Do it by</dt><dd>{hours(item.act_by_hour)}</dd></div></dl>
    <Button disabled={approve.isPending || approve.isSuccess || item.hours_left < 0} onClick={() => {
      setNotice('Sending the crew…');
      approve.mutate({ id: item.plan_id, by: 'MGR-01' }, {
        onSuccess: () => setNotice('Crew is on the way.'),
        onError: () => setNotice('Could not send the crew. Try again.'),
      });
    }}>{approve.isPending ? 'Sending…' : approve.isSuccess ? 'Crew sent' : item.hours_left < 0 ? 'Too late' : 'Send the crew'}</Button>
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
  return <div className="response-view"><h2>What to do first</h2>
    <p className="panel-caption">The best next job. One click texts the crew.</p>
    <Button variant="outline" onClick={() => setPanelView('workorders')}>See crew tasks</Button>
    <RankedList />
    <h3 className="section-title">Open a building to the public</h3><RankedList community />
    <EmergencyNotice />
    <h3 className="section-title">Missed opportunities</h3>
    {missed.isError ? <p role="alert">Missed plans are unavailable.</p> : missed.isPending ? <p role="status">Loading missed plans…</p> : !missed.data.length ? <p className="panel-empty">No missed plans at this step.</p> : missed.data.map(plan => <Card key={plan.id} className="response-card missed-plan">
      <Badge>Missed</Badge><button className="response-building" onClick={() => selectBuilding(plan.building_id)}>{buildings.data?.find(b => b.id === plan.building_id)?.name ?? plan.building_id}</button>
      <h3>{plan.actions?.map(a => a.title).join(' + ') || 'Response plan'}</h3>
      <p>Would have saved <strong>{money(plan.avoided_cents)}</strong>. Too late to send now.</p>
    </Card>)}
    <p className="panel-caption">Sending a job texts the crew. Marking a task done is on Crew tasks.</p>
  </div>;
}
