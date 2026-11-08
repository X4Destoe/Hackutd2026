# Stormi corner assistant

Stormi provides a compact, optional conversation panel for questions about the current exercise, stored reports, and app features. `ChatPanel.tsx` renders conversation entries, suggested questions, loading/error feedback, and a keyboard-accessible composer. It does not call the assistant service or perform operational actions itself; the controller integrates the agreed backend contract.

The launcher, minimize and close controls leave the conversation state with the controller. Escape closes the panel and restores focus to the launcher. The panel has no modal backdrop, so map controls outside it stay usable. Messages render as escaped text, not HTML.

Current integration status: presentation component built and type-checked; service wiring and live-data acceptance await the TASK-059 contract from the backend owner. Do not claim a working report chatbot from this presentation-only checkpoint.
