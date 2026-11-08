import { useState } from 'react';
import type { Model } from '../../../../shared/api';
import { useBuildings, useUpdateWorkOrder, useWorkOrders } from '../../../../shared/queries';
import { useUIStore } from '../../../../shared/ui-store';
import { Badge, Button, Card } from '../../../../shared/ui';
import { CREW_STATUS, taskName } from '../../../../shared/plain';
import './actions.css';

function safePhoto(url: string) {
  try { const parsed = new URL(url); return ['https:', 'http:'].includes(parsed.protocol) ? parsed.href : null; } catch { return null; }
}
function Order({ order, building }: { order: Model<'WorkOrder'>; building: string }) {
  const update = useUpdateWorkOrder();
  const { selectBuilding } = useUIStore();
  const [notice, setNotice] = useState('');
  return <Card className="response-card">
    <div className="response-heading"><strong>{taskName(order.action_code)}</strong><Badge className={`order-status order-${order.status}`}>{CREW_STATUS[order.status] ?? order.status}</Badge></div>
    <button className="response-building" onClick={() => selectBuilding(order.building_id)}>{building}</button>
    <p>{order.text}</p>
    {!!order.updates?.length && <ul className="response-updates" aria-label={`Updates for ${order.id}`}>{order.updates.map((text, i) => <li key={i}>{text}</li>)}</ul>}
    <div className="response-photos">{order.photo_urls?.map((url, i) => {
      const source = safePhoto(url);
      return source ? <a key={`${url}-${i}`} href={source} target="_blank" rel="noopener noreferrer"><img src={source} alt={`Work order ${order.id} photo ${i + 1}`} loading="lazy" referrerPolicy="no-referrer" /></a> : null;
    })}</div>
    {order.status !== 'done' && <div className="response-controls" aria-label={`Update ${order.id}`}>
      {(['accepted', 'blocked', 'done'] as const).map(status => <Button key={status} variant={status === 'done' ? 'primary' : 'outline'} disabled={update.isPending || order.status === status} onClick={() => {
        setNotice('Saving status…');
        update.mutate({ id: order.id, status, note: 'Updated from the crew list.' }, {
          onSuccess: () => setNotice(status === 'done' ? 'Marked done.' : status === 'blocked' ? 'Marked stuck.' : 'Marked started.'),
          onError: () => setNotice('Could not update this task. Try again.'),
        });
      }}>{status === 'done' ? 'Done' : status === 'blocked' ? 'Stuck' : 'Started'}</Button>)}
    </div>}
    {notice && <p role={update.isError ? 'alert' : 'status'}>{notice}</p>}
  </Card>;
}

export default function WorkOrders() {
  const orders = useWorkOrders();
  const buildings = useBuildings();
  const [filter, setFilter] = useState('all');
  const { setPanelView } = useUIStore();
  const visible = orders.data?.filter(o => filter === 'all' || o.status === filter);
  return <div className="response-view"><h2>Crew tasks</h2>
    <p className="panel-caption">Jobs already sent. Tap a status when the situation changes.</p>
    <label className="sort-row">Show<select aria-label="Filter crew tasks" value={filter} onChange={e => setFilter(e.target.value)}>{['all', 'created', 'sent', 'accepted', 'blocked', 'done'].map(s => <option key={s} value={s}>{s === 'all' ? 'All' : CREW_STATUS[s]}</option>)}</select></label>
    {orders.isError ? <div role="alert"><p>Crew tasks are unavailable.</p><Button variant="outline" onClick={() => void orders.refetch()}>Try again</Button></div> : orders.isPending ? <p role="status">Loading tasks…</p> : !visible?.length ? <div className="panel-empty"><p>{orders.data.length ? 'Nothing matches that filter.' : 'No crew tasks yet. Send one from What to do first.'}</p><Button variant="outline" onClick={() => setPanelView('fixfirst')}>What to do first</Button></div> : visible.map(order => <Order key={order.id} order={order} building={buildings.data?.find(b => b.id === order.building_id)?.name ?? order.building_id} />)}
  </div>;
}
