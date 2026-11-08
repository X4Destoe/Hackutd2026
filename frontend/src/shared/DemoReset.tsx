import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { RotateCcw } from 'lucide-react';
import { useDemoState, useMessagingStatus, useReset, useScenarios } from './queries';
import { useUIStore } from './ui-store';
import { Button } from './ui';
import './demo-reset.css';

export default function DemoReset() {
  const state = useDemoState();
  const scenarios = useScenarios();
  const messaging = useMessagingStatus();
  const reset = useReset();
  const { selectBuilding, setPanelView } = useUIStore();
  const [open, setOpen] = useState(false);
  const [scenarioId, setScenarioId] = useState('');
  const [notice, setNotice] = useState('');
  const name = scenarios.data?.find(s => s.id === scenarioId)?.name ?? 'this scenario';
  const changed = Boolean(scenarioId && state.data?.scenario_id !== scenarioId);
  return <>
    <Dialog.Root open={open} onOpenChange={value => {
      if (reset.isPending) return;
      if (value) { setScenarioId(state.data?.scenario_id ?? ''); reset.reset(); setNotice(''); }
      setOpen(value);
    }}>
      <Dialog.Trigger asChild><Button variant="outline" aria-label="Restart current scenario" title="Restart current scenario" disabled={!state.data || state.isError}><RotateCcw size={16} /></Button></Dialog.Trigger>
      <Dialog.Portal><Dialog.Overlay className="dialog-overlay" /><Dialog.Content className="dialog-content demo-reset-dialog"
        onEscapeKeyDown={event => { if (reset.isPending) event.preventDefault(); }}
        onPointerDownOutside={event => { if (reset.isPending) event.preventDefault(); }}>
        <Dialog.Title>Restart scenario?</Dialog.Title>
        <Dialog.Description>Return {name} to its first timeline step. This clears approvals, work orders, messages, resident placements, and reports in the shared demo workspace.</Dialog.Description>
        {messaging.data?.mode === 'photon' && <p>Texts already sent to real phones cannot be recalled. An in-flight send may still finish.</p>}
        {changed && <p role="alert">The scenario changed while this dialog was open. Cancel and reopen it to restart the current exercise.</p>}
        {reset.isError && <p role="alert">Could not confirm the restart. Check your connection and retry.</p>}
        <div className="demo-reset-actions">
          <Dialog.Close asChild><Button variant="outline" disabled={reset.isPending}>Cancel</Button></Dialog.Close>
          <Button disabled={reset.isPending || changed || !scenarioId} onClick={() => reset.mutate(scenarioId, { onSuccess: () => {
            selectBuilding(null); setPanelView('overview'); setOpen(false); setNotice('Scenario restarted. The exercise is ready to begin again.');
          } })}>{reset.isPending ? 'Restarting…' : 'Restart scenario'}</Button>
        </div>
      </Dialog.Content></Dialog.Portal>
    </Dialog.Root>
    <span className="sr-only" role="status">{notice}</span>
  </>;
}
