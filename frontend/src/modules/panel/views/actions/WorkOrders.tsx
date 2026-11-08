import { useState } from 'react';
import type { Model } from '../../../../shared/api';
import { useBuildings, useUpdateWorkOrder, useWorkOrders } from '../../../../shared/queries';
import { useUIStore } from '../../../../shared/ui-store';
import { Badge, Button, Card } from '../../../../shared/ui';
import './actions.css';

function safePhoto(url: string) {
  try { const parsed = new URL(url); return ['https:', 'http:'].includes(parsed.protocol) ? parsed.href : null; } catch { return null; }
}
function Order({ order, building }: { order: Model<'WorkOrder'>; building: string }) {
  const update = useUpdateWorkOrder();
  const { selectBuilding } = useUIStore();
  const [notice, setNotice] = useState('');
  return <Card className="response-card">
    <div className="response-heading"><strong>{order.id}</strong><Badge className={`order-status order-${order.status}`}>{order.status}</Badge></div>
    <button className="response-building" onClick={() => selectBuilding(order.building_id)}>{building}</button>
    <p>{order.text}</p><p className="panel-caption">Assignee: {order.party_id} · Plan {order.plan_id}</p>
    {!!order.updates?.length && <ul className="response-updates" aria-label={`Updates for ${order.id}`}>{order.updates.map((text, i) => <li key={i}>{text}</li>)}</ul>}
    <div className="response-photos">{order.photo_urls?.map((url, i) => {
      const source = safePhoto(url);
      return source ? <a key={`${url}-${i}`} href={source} target="_blank" rel="noopener noreferrer"><img src={source} alt={`Work order ${order.id} photo ${i + 1}`} loading="lazy" referrerPolicy="no-referrer" /></a> : null;
    })}</div>
    {order.status !== 'done' && <div className="response-controls" aria-label={`Update ${order.id}`}>
      {(['accepted', 'blocked', 'done'] as const).map(status => <Button key={status} variant={status === 'done' ? 'primary' : 'outline'} disabled={update.isPending || order.status === status} onClick={() => {
        setNotice('Saving status…');
        update.mutate({ id: order.id, status, note: 'Manual status update from portfolio manager.' }, {
          onSuccess: () => setNotice(`Work order marked ${status}.`),
          onError: () => setNotice('Status update failed. Please retry.'),
        });
      }}>{status === 'done' ? 'Mark done' : status === 'blocked' ? 'Mark blocked' : 'Accept'}</Button>)}
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
  return <div className="response-view"><h2>Work Orders</h2>
    <p className="panel-caption">Dispatch, technician replies and completion updates refresh live.</p>
    <label className="sort-row">Status<select aria-label="Filter work orders by status" value={filter} onChange={e => setFilter(e.target.value)}>{['all', 'created', 'sent', 'accepted', 'blocked', 'done'].map(s => <option key={s} value={s}>{s === 'all' ? 'All statuses' : s}</option>)}</select></label>
    {orders.isError ? <div role="alert"><p>Work orders are unavailable.</p><Button variant="outline" onClick={() => void orders.refetch()}>Retry work orders</Button></div> : orders.isPending ? <p role="status">Loading work orders…</p> : !visible?.length ? <div className="panel-empty"><p>{orders.data.length ? 'No work orders match this status.' : 'No work orders yet. Approve a Fix-First plan to create response tasks.'}</p><Button variant="outline" onClick={() => setPanelView('fixfirst')}>Open Fix-First</Button></div> : visible.map(order => <Order key={order.id} order={order} building={buildings.data?.find(b => b.id === order.building_id)?.name ?? order.building_id} />)}
  </div>;
}
