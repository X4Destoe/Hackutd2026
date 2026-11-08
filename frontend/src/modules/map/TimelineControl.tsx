// Vertical timeline on the map's left edge (like the UTD map's floor selector). ←/→ or ▲/▼ step through the scenario.
import { useEffect } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { useDemoState, useSetHour, useTimeline } from '../../shared/queries';
import { phaseColor, type Phase } from '../../shared/format';

export default function TimelineControl() {
  const steps = useTimeline();
  const state = useDemoState();
  const setHour = useSetHour();
  const hours = (steps.data ?? []).map((s) => s.hour);
  const current = state.data?.step_hour;
  const index = current === undefined ? -1 : hours.indexOf(current);
  const go = (delta: number) => {
    const next = hours[index + delta];
    if (next !== undefined && !setHour.isPending) setHour.mutate(next);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName))) return;
      if (e.key === 'ArrowRight') go(1);
      if (e.key === 'ArrowLeft') go(-1);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  if (!steps.data?.length) return null;
  return (
    <nav className="storm-timeline" aria-label="Disaster timeline">
      <button type="button" className="storm-timeline-arrow" aria-label="Earlier step" disabled={index <= 0} onClick={() => go(-1)}>
        <ChevronUp size={16} />
      </button>
      {steps.data.map((s) => {
        const [time, label] = s.label.split(' · ');
        return (
          <button key={s.hour} type="button" aria-pressed={s.hour === current} title={s.narrative}
            style={{ borderLeftColor: phaseColor(s.phase as Phase) }} onClick={() => !setHour.isPending && setHour.mutate(s.hour)}>
            <strong>{time}</strong>
            <span>{label ?? s.phase}</span>
          </button>
        );
      })}
      <button type="button" className="storm-timeline-arrow" aria-label="Later step" disabled={index < 0 || index >= hours.length - 1} onClick={() => go(1)}>
        <ChevronDown size={16} />
      </button>
    </nav>
  );
}
