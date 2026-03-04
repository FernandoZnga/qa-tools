# QA Tools (Django + Docker)

This project is a QA workbench for API testing and lightweight load testing.

Use it to:
- Store environments and variables (`TOKEN`, `BASE_URL`, etc.)
- Format and validate JSON/XML payloads
- Send ad-hoc API requests or saved request templates
- Track request run logs (status code, response time, payload)
- Generate random test data
- Run sync or async load tests with Celery workers
- Export saved templates/runs to Postman format

## Tech Stack
- Python 3.12
- Django + Django REST Framework
- PostgreSQL
- Redis + Celery
- Docker Compose

## Quick Start
1. Create env file:
```bash
cp .env.example .env
```
2. Start everything:
```bash
make up
```
3. Open app:
- `http://localhost:8000/`
4. Open admin:
- `http://localhost:8000/admin/`
- user: `admin`
- pass: `admin12345`

## Common Commands
```bash
make up            # build + run web, worker, db, redis
make down          # stop all services
make logs          # follow web logs
make logs-worker   # follow celery worker logs
make migrate       # run Django migrations in web container
make shell         # open Django shell in web container
```

## UI Pages
- `/` home
- `/formatter/` JSON/XML formatter
- `/diff/` text/file diff
- `/api/` single API sender
- `/stress/` load test launcher
- `/data/` random data generator
- `/runs/` async run status

## Example Workflows

### 1) Format JSON before sending
Endpoint: `POST /api/formatter/format/`

```json
{
  "format": "json",
  "action": "pretty",
  "input": "{\"a\":1,\"b\":2}"
}
```

### 2) Send a single API request with environment variables
Endpoint: `POST /api/client/send/`

```json
{
  "method": "POST",
  "url": "https://httpbin.org/post",
  "headers": {
    "Authorization": "Bearer {{TOKEN}}"
  },
  "query_params": {
    "source": "qa"
  },
  "body_type": "json",
  "body": "{\"name\":\"qa\",\"active\":true}",
  "timeout_seconds": 20,
  "environment_id": 1
}
```

### 3) Run async load test in background
Endpoint: `POST /api/client/load-test/run-async/`

```json
{
  "template_id": 1,
  "total_requests": 100,
  "mode": "multi",
  "concurrency": 20,
  "delay_ms": 0,
  "environment_id": 1
}
```

The async endpoint returns `load_run_id` and `task_id`.  
Poll status with: `GET /api/client/load-runs/{load_run_id}/`

### 4) Generate random test data
- `GET /api/core/random-data/?count=5`
- `POST /api/core/random-data/generate/`
- `GET /api/core/random-data/providers/?locale=en_US`

## Core API Surface

### Environment management
- `GET/POST /api/core/environments/`
- `GET/PUT/DELETE /api/core/environments/{id}/`
- `GET/POST /api/core/environment-variables/`

### API templates
- `GET/POST /api/client/templates/`
- `GET/PUT/DELETE /api/client/templates/{id}/`
- `GET /api/client/templates/{id}/export-postman/`

### Run logs
- `GET /api/client/run-logs/`
- `GET /api/client/run-logs/{id}/`

### Load scenarios and runs
- `GET/POST /api/client/load-scenarios/`
- `GET/PUT/DELETE /api/client/load-scenarios/{id}/`
- `POST /api/client/load-test/run/` (sync)
- `POST /api/client/load-test/run-async/` (async)
- `GET /api/client/load-runs/`
- `GET /api/client/load-runs/{id}/`
- `GET /api/client/load-runs/{id}/export-postman/`

## Placeholder Variables
Use placeholders like `{{KEY}}` in URL, headers, query params, and body.  
They are resolved from the selected `environment_id`.

## Services in Docker Compose
- `web`: Django app (Gunicorn)
- `worker`: Celery worker for async load runs
- `db`: PostgreSQL 16
- `redis`: broker/result backend

## Notes
- Migrations run automatically in `web` when `RUN_MIGRATIONS=true`.
- Static files are collected in `web` when `RUN_COLLECTSTATIC=true`.
- Worker has both flags disabled by default.
