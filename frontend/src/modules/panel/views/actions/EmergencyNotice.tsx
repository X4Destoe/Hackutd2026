import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useBuildings, useDemoState, useMessagingStatus, invalidateKeys } from '../../../../shared/queries';
import type { Model } from '../../../../shared/api';
import { Button, Card } from '../../../../shared/ui';

type Receipt = { messages: Model<'Message'>[]; duplicate: boolean };
export default function EmergencyNotice() {
  const buildings = useBuildings();
  const state = useDemoState();
  const status = useMessagingStatus();
  const client = useQueryClient();
  const [buildingId, setBuildingId] = useState('');
  const [tenants, setTenants] = useState<string[]>([]);
  const [text, setText] = useState('');
  const [preview, setPreview] = useState(false);
  const [requestId, setRequestId] = useState('');
  const [context, setContext] = useState<{scenario_id: string; step_hour: number; mode: string} | null>(null);
  const building = buildings.data?.find(b => b.id === buildingId);
  const send = useMutation({
    mutationFn: async (payload: object): Promise<Receipt> => {
      const response = await fetch('/api/customer-notices', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(typeof body.detail === 'string' ? body.detail : 'Notice could not be submitted.'); }
      return response.json();
    },
    onSuccess: () => invalidateKeys(client, ['messages', 'messagingStatus']),
  });
  const edit = () => { setPreview(false); setRequestId(''); send.reset(); };
  const eligible = !!building && tenants.length > 0 && !!text.trim() && !!state.data && !!status.data && !state.isFetching;
  return <Card className="response-card"><h3>Customer emergency notice</h3>
    <p>Text the tenants in one building.</p>
    <p className="panel-caption">{status.data?.mode === 'photon' ? 'Photon enabled. Only configured live contacts receive real texts; other contacts use the simulator.' : 'Simulator: no real texts will be sent.'}</p>
    <form className="phone-simulator" onSubmit={e => { e.preventDefault(); if (!eligible) return; setRequestId(crypto.randomUUID()); setContext({ scenario_id: state.data!.scenario_id, step_hour: state.data!.step_hour, mode: status.data!.mode }); setPreview(true); }}>
      <label>Notice building<select aria-label="Notice building" value={buildingId} disabled={send.isPending || preview} onChange={e => { edit(); setBuildingId(e.target.value); setTenants([]); }} required>
        <option value="">Choose building</option>{buildings.data?.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
      </select></label>
      {buildings.isError && <p role="alert">Buildings unavailable. Reconnect before preparing a notice.</p>}
      {building && <fieldset disabled={send.isPending || preview}><legend>Tenant contacts</legend>{building.tenants?.map(t => <label key={t.id} className="panel-check"><input type="checkbox" disabled={!t.contact_party_id} checked={tenants.includes(t.id)} onChange={e => { edit(); setTenants(current => e.target.checked ? [...current, t.id] : current.filter(id => id !== t.id)); }} />{t.name}{!t.contact_party_id && ' · No contact configured'}</label>)}</fieldset>}
      <label>Emergency instructions<textarea aria-label="Emergency instructions" rows={4} maxLength={1600} required disabled={send.isPending || preview} value={text} onChange={e => { edit(); setText(e.target.value); }} placeholder="Ground floor closes at 16:00. Move equipment to level 2. Reply if you need assistance." /></label>
      {!preview && <Button type="submit" disabled={!eligible}>Preview customer notice</Button>}
    </form>
    {preview && <section aria-label="Notice preview"><h3>Review before sending</h3><p className="message-body">Operation Storm | {building?.name}{'\n'}{text.trim()}</p><p>Recipients: {building?.tenants?.filter(t => tenants.includes(t.id)).map(t => t.name).join(', ')}</p>
      <p className="panel-caption">Only send instructions reviewed by your response team. Photon acceptance does not confirm customer delivery.</p>
      <div className="response-controls"><Button disabled={!eligible || send.isPending || send.isSuccess || send.isError} onClick={() => send.mutate({ request_id: requestId, scenario_id: context!.scenario_id, step_hour: context!.step_hour, building_id: buildingId, tenant_ids: tenants, text: text.trim(), mode: context!.mode })}>{send.isPending ? 'Submitting notice…' : status.data?.mode === 'photon' ? 'Send customer notice' : 'Simulate customer notice'}</Button>
      <Button variant="outline" disabled={send.isPending} onClick={edit}>{send.isSuccess || send.isError ? 'Prepare another notice' : 'Edit notice'}</Button></div>
    </section>}
    {send.isError && <p role="alert">{send.error.message} Delivery outcome may be unknown; check Texts before preparing another notice. No automatic resend.</p>}
    {send.data && <div role="status"><h3>Notice results</h3>{send.data.messages.map(m => <p key={m.id}>{m.party_id}: {m.channel === 'sim' ? 'Simulator' : 'Photon'} · {m.status === 'sent' ? m.channel === 'sim' ? 'recorded (no real text)' : 'accepted by provider (delivery unconfirmed)' : m.status}{m.error ? ` · ${m.error}` : ''}</p>)}</div>}
  </Card>;
}
