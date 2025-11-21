# Vysalytica API

Production-ready Flask backend for the Vysalytica AI Visibility Audit tool. The service is ready to pair with the Next.js frontend, ships with health/version discovery endpoints, and includes CI/test automation.

## Quickstart

```bash
cp .env.example .env
make install
make dev  # serves http://localhost:8000
```

Key commands:
- `make run` – production-style Gunicorn start
- `make test` – pytest suite with coverage shim
- `make lint` / `make format` – Ruff + Black/Isort

## Environment variables

`.env.example` documents defaults:

- `FLASK_ENV=development`
- `DATABASE_URL=sqlite:///api/data/vysalytica.db`
- `SECRET_KEY=changeme`
- `RATE_LIMIT=60/minute`
- `CORS_ORIGINS=http://localhost:3000,https://*.onrender.com`
- `LOG_LEVEL=INFO`

Additional runtime knobs:
- `LIMITER_STORAGE_URI` (e.g., `memory://` for dev, `redis://` in prod)
- `WIDGET_ALLOWED_ORIGINS` to constrain unauthenticated widget calls
- `QUICKSCAN_CACHE_ENABLED` / `QUICKSCAN_CACHE_TTL_SECONDS` for caching

## Running locally

- Dev server: `make dev` (Flask reloader)
- Gunicorn: `make run` or `heroku local` with the provided `Procfile`
- Health: `curl http://localhost:8000/healthz`
- Version: `curl http://localhost:8000/version`

SQLite lives at `api/data/vysalytica.db` by default. Reset it with:

```bash
python scripts/dev_db_reset.py
```

## Frontend integration

- **Base URL:** `http://localhost:8000`
- **CORS:** Allowed origins come from `CORS_ORIGINS` (comma separated, wildcards supported). Credentials are enabled and `Content-Disposition` is exposed for downloads.
- **Preflight:** Generic `OPTIONS` handlers are registered for all paths.
- **Error shape:** `{ "error": { "code": "string", "message": "string" } }`

### Core endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/healthz` | Liveness + DB probe |
| GET | `/version` | Git SHA and build metadata |
| GET | `/openapi.json` | Lightweight route listing |
| GET | `/api/health` | Legacy health check |
| GET | `/api/version` | Legacy version info |
| POST | `/api/audit` | Run an audit (JSON or DOCX) |

Example audit request:

```bash
curl -X POST http://localhost:8000/api/audit \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com", "packs": ["base"], "plan": "quickscan"}'
```

Example audit JSON response (truncated):

```json
{
  "success": true,
  "data": {
    "audit_id": 1,
    "url": "https://example.com",
    "domain": "example.com",
    "page_count": 3,
    "scores": { "overall": 80.0, "by_category": {"base": 80.0} },
    "findings": [ ... ]
  }
}
```

## Logging

Structured JSON logs are emitted to stdout and honor `LOG_LEVEL`. Proxy headers are trusted for rate limiting when running behind load balancers.

## Deployment (Render/Heroku)

- `Procfile`: `web: PYTHONPATH=. gunicorn api:app --workers 2 --threads 4 --timeout 120`
- `render.yaml` included for Render one-click deploy (health check `/healthz`).
- Default to SQLite if `DATABASE_URL` is not set; Postgres is recommended for production.

## Testing & CI

GitHub Actions (`.github/workflows/ci.yml`) runs Ruff, Black checks, and the pytest suite with coverage output. Local `make test` uses the same entry point. If offline, stub coverage plugins in `vendor/` keep the suite runnable.
