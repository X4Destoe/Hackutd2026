import { useEffect, useId, useRef, useState } from 'react';
import { MessageSquare, Minus, Send, X } from 'lucide-react';
import './assistant.css';

export type ChatEntry = { id: string; role: 'user' | 'assistant'; text: string; source?: string };
type Props = {
  entries: ChatEntry[]; pending: boolean; error: string; context: string;
  onAsk: (question: string) => void; onClear: () => void;
};
const starters = ['Summarize the latest report', 'What does estimated loss mean?',
  'Which actions should I prioritize?', 'How do I update a work order?'];

export default function ChatPanel({ entries, pending, error, context, onAsk, onClear }: Props) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const panelId = useId();
  const launcher = useRef<HTMLButtonElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { if (open) input.current?.focus(); }, [open]);
  useEffect(() => { if (open) end.current?.scrollIntoView({ block: 'nearest' }); }, [entries.length, pending, open]);
  const hide = () => { setOpen(false); launcher.current?.focus(); };
  const submit = (question: string) => {
    if (!question.trim() || pending) return;
    onAsk(question.trim()); setDraft('');
  };
  return <div className="storm-assistant">
    <button ref={launcher} className="assistant-launcher" aria-label={open ? 'Minimize Stormi assistant' : 'Open Stormi assistant'}
      aria-expanded={open} aria-controls={panelId} onClick={() => setOpen(value => !value)}>
      <MessageSquare size={18} aria-hidden="true" /><span>Ask Stormi</span>
    </button>
    <section id={panelId} className="assistant-panel" role="region" aria-label="Stormi assistant" hidden={!open}
      onKeyDown={event => { if (event.key === 'Escape') { event.stopPropagation(); hide(); } }}>
      <header className="assistant-header"><div><h2>Stormi</h2><p>Reports, response plans & app help</p></div>
        <button aria-label="Minimize assistant" title="Minimize" onClick={hide}><Minus size={18} /></button>
        <button aria-label="Close assistant" title="Close" onClick={hide}><X size={18} /></button>
      </header>
      <p className="assistant-context">{context}</p>
      <div className="assistant-conversation" role="log" aria-label="Assistant conversation" aria-live="polite" aria-relevant="additions text" aria-busy={pending}>
        {!entries.length && <div className="assistant-welcome"><h3>What would you like to know?</h3>
          <p>Ask about the current exercise, explain a report, or get help using a feature.</p>
          <div className="assistant-starters">{starters.map(question => <button key={question} disabled={pending} onClick={() => submit(question)}>{question}</button>)}</div>
        </div>}
        {entries.map(entry => <article key={entry.id} className={`assistant-message assistant-${entry.role}`}>
          <strong>{entry.role === 'user' ? 'You' : 'Stormi'}</strong><p>{entry.text}</p>{entry.source && <small>{entry.source}</small>}
        </article>)}
        {pending && <p role="status" className="assistant-thinking">Checking the current records…</p>}
        <div ref={end} />
      </div>
      {error && <p className="assistant-error" role="alert">{error}</p>}
      <form className="assistant-composer" onSubmit={event => { event.preventDefault(); submit(draft); }}>
        <label className="sr-only" htmlFor={`${panelId}-question`}>Ask Stormi a question</label>
        <textarea ref={input} id={`${panelId}-question`} rows={2} maxLength={1200} value={draft} disabled={pending}
          placeholder="Ask about this report or a feature…" onChange={event => setDraft(event.target.value)}
          onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); submit(draft); } }} />
        <button type="submit" aria-label="Send assistant question" disabled={pending || !draft.trim()}><Send size={17} /></button>
      </form>
      <footer><span>Answers explain records; actions stay in your control.</span>
        <button disabled={pending || !entries.length} onClick={onClear}>Clear chat</button>
      </footer>
    </section>
  </div>;
}
