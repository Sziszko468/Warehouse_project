# StockFlow

A classic warehouse management system REST API — products, categories, warehouses, suppliers,
stock in/out/transfer with a full audit trail, and low-stock alerts.

- **FastAPI** + **SQLAlchemy 2.0** + **PostgreSQL** + **Alembic**
- JWT auth with **Admin** / **Staff** roles
- **Docker Compose** (Postgres + Adminer + the API)
- **Swagger** / OpenAPI docs at `/docs`
- **pytest** test suite (50 tests, SQLite in-memory, no Docker required to run)

## Quickstart (Docker)

```bash
cp .env.example .env
docker compose up --build
```

This starts Postgres, runs the Alembic migrations, and boots the API on
[http://localhost:8000](http://localhost:8000) (docs at `/docs`). On first boot the app creates
an admin account from `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` in `.env` — log in with those
to get started, no manual DB step needed.

[Adminer](http://localhost:8080) (a DB browser) is also available — server `postgres`, and the
credentials from `.env`.

To load some electronics-wholesaler-flavored demo data (categories, suppliers, warehouses,
products, and initial stock):

```bash
docker compose exec api uv run python -m app.seed
```

## Local development (without Docker)

Requires [uv](https://docs.astral.sh/uv/) and a running Postgres (e.g. `docker compose up -d postgres`).

```bash
cp .env.example .env               # then adjust DATABASE_URL to point at localhost if needed
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Run the test suite (SQLite in-memory, no Postgres needed):

```bash
uv run pytest
```

Lint:

```bash
uv run ruff check .
uv run ruff format .
```

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

## Known limitation

The test suite runs against SQLite in-memory for speed, and SQLite silently no-ops `SELECT ...
FOR UPDATE`. The row-locking behavior itself is only meaningfully exercised against real
Postgres — the tests verify correct *outcomes* (sequential in/out/transfer calls, insufficient
stock, self-transfer rejection) rather than true concurrent-request locking.

## Environment variables

See [.env.example](.env.example). `DATABASE_URL` should use the `postgres` hostname when run via
Docker Compose (the compose file sets this for you) and `localhost` when running the app directly
on the host against a Dockerized or local Postgres.
