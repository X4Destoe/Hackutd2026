# Corner assistant

The corner widget explains current scenario records and app features. It does not approve plans or send operational messages. `ChatPanel` is a presentation component; its controller adapts the agreed backend assistant contract.

Closing/minimizing preserves the current conversation. Scenario context changes invalidate old answers; in-flight responses must never appear as answers for a newer scenario or selected building. No additional EventSource is created.
