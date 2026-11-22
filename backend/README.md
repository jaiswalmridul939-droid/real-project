# Backend

FastAPI API for Claim What's Yours. The local demo uses SQLite; Docker Compose uses PostgreSQL.

## Local setup

```powershell
py -m pip install -r requirements.txt
py -m alembic upgrade head
py seed.py
py -m uvicorn app.main:app --reload
```

Run the test suite with `py -m pytest tests -q`. For PostgreSQL, install `requirements-postgres.txt` and set `DATABASE_URL` to a `postgresql+psycopg://` URL. The optional Claude extractor uses `CLAUDE_API_KEY`; without it, a manual fallback is used. Set `ENABLE_SCHEDULER=true` to enable daily deadline reminders and mock outbox delivery.

Scheme summaries are demo data. Dates reflect an official portal check on 21 Nov 2026 for eight reachable source entries; Namo Shetkari and PMKSY intentionally retain the outdated sentinel. Portal reachability does not verify sample eligibility rules or deadlines. Confirm those before presenting.