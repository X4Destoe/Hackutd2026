# actions

Plans with cost, avoided dollars, ROI and act-by; Fix-First; approve / reject.
- `catalog.py`: the action catalog. `plans.py`: greedy plan building, missed plans, Fix-First. `__init__.py`: public API + events.
  `routes.py`: HTTP. `execute.py` (TASK-021): work orders and texts on approval.
- Tests: `cd backend && python -m pytest app/modules/actions`.
