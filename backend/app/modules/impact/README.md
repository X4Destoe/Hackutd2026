# impact

The CBRE core: per building, what this disaster costs the business, and why.

- `constants.py`: curves and constants (PRD 03 §3). `model.py`: pure money model. `__init__.py`: wiring, cache, summary,
  `site_safe`. `routes.py`: HTTP.
- Tests: `cd backend && python -m pytest app/modules/impact`.
