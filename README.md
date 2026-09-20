# StockFlow

**Languages:** English (this file) · [Magyar](README.hu.md)

A classic warehouse management system — products, categories, warehouses, suppliers, stock
in/out/transfer with a full audit trail, and low-stock alerts. REST API backend with a Hungarian,
steampunk-themed web frontend.

- **FastAPI** + **SQLAlchemy 2.0** + **PostgreSQL** + **Alembic**
- JWT auth with **Admin** / **Staff** roles
- **Celery** + **Redis** for background jobs (email notifications, a daily scheduled stock report)
- **React 19** + **TypeScript** + **Vite** frontend (`frontend/`), Hungarian UI
- **Docker Compose** (Postgres + Redis + Adminer + the API + Celery worker/beat + the frontend)
- **GitHub Actions** CI (backend lint/tests, frontend lint/build) on every push/PR
- **Swagger** / OpenAPI docs at `/docs`
- **pytest** test suite (SQLite in-memory, no Docker required to run)

## Quickstart (Docker)

```bash
cp .env.example .env
docker compose up --build
```

This starts Postgres, Redis, runs the Alembic migrations, boots the API on
[http://localhost:8000](http://localhost:8000) (docs at `/docs`), starts the Celery worker and
beat scheduler (background jobs — see [Background jobs](#background-jobs) below), and serves the
frontend on [http://localhost:5173](http://localhost:5173). On first API boot the app creates an
admin account from `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` in `.env` — log in with those (in
the web UI or via `/docs`) to get started, no manual DB step needed.

[Adminer](http://localhost:8080) (a DB browser) is also available. Log in with the values from
`.env` (defaults shown below) — note the server is the Docker service name `postgres`, not
`localhost`, since Adminer reaches it over the Docker network:

| Field | Value |
|---|---|
| System | PostgreSQL |
| Server | `postgres` |
| Username | `stockflow` (`POSTGRES_USER`) |
| Password | `stockflow` (`POSTGRES_PASSWORD`) |
| Database | `stockflow` (`POSTGRES_DB`) |

To load some electronics-wholesaler-flavored demo data (categories, suppliers, warehouses,
products, and initial stock):

```bash
docker compose exec api uv run python -m app.seed
```

Rebuild just the frontend after pulling changes (e.g. if `VITE_API_URL` needs to point somewhere
other than `http://localhost:8000`, pass it as a build arg):

```bash
docker compose up --build frontend
```

## Local development (without Docker)

### Backend

Requires [uv](https://docs.astral.sh/uv/) and a running Postgres (e.g. `docker compose up -d postgres`).

```bash
cp .env.example .env               # then adjust DATABASE_URL to point at localhost if needed
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Run the test suite (SQLite in-memory, no Postgres/Redis needed — Celery tasks run synchronously
in-process during tests):

```bash
uv run pytest
```

Lint:

```bash
uv run ruff check .
uv run ruff format .
```

### Frontend

Requires Node 22+. Point it at a running backend (Docker or local) via `frontend/.env`:

```bash
cd frontend
cp .env.example .env               # VITE_API_URL, defaults to http://localhost:8000
npm install
npm run dev                        # http://localhost:5173, hot reload
```

`npm run build` produces a production build in `frontend/dist`; `npm run lint` runs oxlint.

## Roles

- **Admin** — full access: manage users, products, categories, warehouses, suppliers, and stock.
- **Staff** — can read everything and perform stock in/out/transfer, but cannot manage master
  data (products/categories/warehouses/suppliers) or users.

`POST /auth/register` always creates a **Staff** account; there's no way to self-escalate to
Admin through the API. Promote a user via `PATCH /users/{id}` as an existing Admin.

## Stock model

Current stock is tracked per `(product, warehouse)` pair. Every `stock/in`, `stock/out`, and
`stock/transfer` call also writes an immutable `StockMovement` audit row, viewable via
`GET /stock/movements`. Stock mutations row-lock the affected `Stock` row(s) (`SELECT ... FOR
UPDATE`) so concurrent requests can't overdraw the same stock; a `CHECK (quantity >= 0)`
constraint is a hard backstop. `GET /stock/low-stock` lists `(product, warehouse)` rows at or
below that product's `min_stock_threshold`.

## Background jobs

Email notifications (purchase order submitted/received, a customer order fully shipped, a
low-stock crossing) and a daily stock-valuation report (emailed to all active admins, 06:00 UTC)
run as **Celery** tasks against a **Redis** broker, rather than inline in the API process — so
they're retried on a transient failure and don't get lost if the API restarts mid-request. Under
Docker Compose this is the `redis`, `celery_worker`, and `celery_beat` services, started
automatically by `docker compose up`.

Running the worker/beat locally (outside Docker), against a Dockerized Redis:

```bash
docker compose up -d redis
uv run celery -A app.celery_app:celery_app worker --loglevel=info   # separate terminal
uv run celery -A app.celery_app:celery_app beat --loglevel=info     # another separate terminal
```

If Redis isn't reachable when a request tries to enqueue a job (e.g. running the API alone
without the worker), the enqueue failure is logged and swallowed — it never breaks the request
that triggered it (see `app.celery_app.enqueue`).

## Known limitation

The test suite runs against SQLite in-memory for speed, and SQLite silently no-ops `SELECT ...
FOR UPDATE`. The row-locking behavior itself is only meaningfully exercised against real
Postgres — the tests verify correct *outcomes* (sequential in/out/transfer calls, insufficient
stock, self-transfer rejection) rather than true concurrent-request locking.

## Environment variables

See [.env.example](.env.example). `DATABASE_URL` should use the `postgres` hostname when run via
Docker Compose (the compose file sets this for you) and `localhost` when running the app directly
on the host against a Dockerized or local Postgres.
