# DT-Labs (LIS MVP)

FastAPI + PostgreSQL (async) + Jinja2 templates + GraphQL (Strawberry) + ASTM integration scaffold.

## Quick start

1. Create and activate a virtualenv
2. Install deps:
   - `pip install -r requirements.txt`
3. Set environment:
   - copy `.env.example` to `.env` and edit values
4. Run:
   - `uvicorn app.main:app --reload`

## Seed initial analyzers/tests
After you create DB tables (via Alembic), you can seed:
- `integration/seed/seed.json`

A seed helper is provided in `app/services/seed_service.py`.


## Analyzer Listener Service
Run as a separate process (recommended) to listen to analyzers and POST results into the LIS.

```bash
python -m integration.listener_service.run
```
## It will:

- load analyzers from DB
- start listeners
- send ingests into FastAPI

Ensure `.env` includes:
- `DATABASE_URL=postgresql+asyncpg://...`
- `INGEST_TOKEN=...` (must match LIS)
- `LIS_BASE_URL=http://127.0.0.1:8000`
