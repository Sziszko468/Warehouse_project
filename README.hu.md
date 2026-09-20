# StockFlow

**Nyelvek:** [English](README.md) · Magyar (ez a fájl)

Klasszikus raktárkezelő rendszer — termékek, kategóriák, raktárak, beszállítók, készlet
bevételezés/kiadás/áthelyezés teljes naplózással, és alacsony készlet jelzések. REST API backend
magyar nyelvű, steampunk stílusú webes felülettel.

- **FastAPI** + **SQLAlchemy 2.0** + **PostgreSQL** + **Alembic**
- JWT alapú hitelesítés **Admin** / **Munkatárs** szerepkörökkel
- **React 19** + **TypeScript** + **Vite** frontend (`frontend/`), magyar nyelvű felület
- **Docker Compose** (Postgres + Adminer + API + frontend)
- **Swagger** / OpenAPI dokumentáció a `/docs` címen
- **pytest** tesztkészlet (50 teszt, SQLite memóriában, Docker nélkül futtatható)

## Gyors indítás (Docker)

```bash
cp .env.example .env
docker compose up --build
```

Ez elindítja a Postgres-t, lefuttatja az Alembic migrációkat, elindítja az API-t a
[http://localhost:8000](http://localhost:8000) címen (dokumentáció: `/docs`), és kiszolgálja a
frontendet a [http://localhost:5173](http://localhost:5173) címen. Az API első indításakor a
rendszer létrehoz egy admin fiókot a `.env`-ben megadott `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD`
alapján — ezzel tud belépni (a webes felületen vagy a `/docs`-on keresztül), manuális
adatbázis-lépés nélkül.

Az [Adminer](http://localhost:8080) (adatbázis-böngésző) szintén elérhető. Belépéshez a
`.env`-ben megadott adatokat használd (alapértelmezett értékek lent) — a szerver a Docker
szolgáltatásnév `postgres`, **nem** `localhost`, mivel az Adminer a Docker hálózaton keresztül éri
el az adatbázist:

| Mező | Érték |
|---|---|
| Rendszer | PostgreSQL |
| Szerver | `postgres` |
| Felhasználónév | `stockflow` (`POSTGRES_USER`) |
| Jelszó | `stockflow` (`POSTGRES_PASSWORD`) |
| Adatbázis | `stockflow` (`POSTGRES_DB`) |

Elektronikai nagykereskedés hangulatú demóadatok betöltéséhez (kategóriák, beszállítók, raktárak,
termékek és kezdő készlet):

```bash
docker compose exec api uv run python -m app.seed
```

A frontend újraépítése frissítés után (pl. ha a `VITE_API_URL`-nak máshova kell mutatnia, mint a
`http://localhost:8000`, adja meg build argumentumként):

```bash
docker compose up --build frontend
```

## Helyi fejlesztés (Docker nélkül)

### Backend

Szükséges hozzá [uv](https://docs.astral.sh/uv/) és egy futó Postgres (pl. `docker compose up -d postgres`).

```bash
cp .env.example .env               # majd állítsa a DATABASE_URL-t localhost-ra, ha szükséges
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Tesztek futtatása (SQLite memóriában, Postgres nem szükséges):

```bash
uv run pytest
```

Lint:

```bash
uv run ruff check .
uv run ruff format .
```

### Frontend

Szükséges hozzá Node 22+. Állítsa be, hogy melyik backendhez csatlakozzon (Docker vagy helyi) a
`frontend/.env` fájlban:

```bash
cd frontend
cp .env.example .env               # VITE_API_URL, alapértelmezetten http://localhost:8000
npm install
npm run dev                        # http://localhost:5173, hot reload
```

`npm run build` létrehoz egy production buildet a `frontend/dist` mappában; `npm run lint`
lefuttatja az oxlint-et.

## Szerepkörök

- **Admin** — teljes hozzáférés: felhasználók, termékek, kategóriák, raktárak, beszállítók és
  készlet kezelése.
- **Munkatárs (Staff)** — mindent olvashat, és végrehajthat készletbevételezést, -kiadást és
  -áthelyezést, de nem kezelheti a törzsadatokat (termékek/kategóriák/raktárak/beszállítók) vagy a
  felhasználókat.

A `POST /auth/register` mindig **Munkatárs** fiókot hoz létre; az API-n keresztül nincs mód
önmagunkat Adminná léptetni. Egy felhasználót egy meglévő Admin léptethet elő a
`PATCH /users/{id}` végponton keresztül.

## Készletmodell

Az aktuális készletet a rendszer `(termék, raktár)` páronként tartja nyilván. Minden `stock/in`,
`stock/out` és `stock/transfer` hívás emellett egy megváltoztathatatlan `StockMovement`
naplóbejegyzést is létrehoz, amely a `GET /stock/movements` végponton tekinthető meg. A
készletváltoztató műveletek zárolják (`SELECT ... FOR UPDATE`) az érintett `Stock` sor(oka)t, hogy
egyidejű kérések ne tudják túllépni a rendelkezésre álló készletet; egy `CHECK (quantity >= 0)`
megkötés pedig biztonsági tartalékként szolgál. A `GET /stock/low-stock` azokat a
`(termék, raktár)` sorokat listázza, amelyek elérték vagy alulmúlják az adott termék
`min_stock_threshold` értékét.

## Ismert korlátozás

A tesztkészlet a sebesség érdekében SQLite memóriában fut, az SQLite pedig csendben figyelmen
kívül hagyja a `SELECT ... FOR UPDATE`-ot. Maga a sorzárolási viselkedés emiatt csak valódi
Postgres ellen tesztelhető érdemben — a tesztek a helyes *eredményeket* ellenőrzik (egymást követő
be/ki/áthelyezés hívások, elégtelen készlet, önmagába történő áthelyezés elutasítása), nem pedig a
valós egyidejű zárolást.

## Környezeti változók

Lásd: [.env.example](.env.example). A `DATABASE_URL`-nak a `postgres` hostnevet kell használnia
Docker Compose-ban futtatva (ezt a compose fájl automatikusan beállítja), és a `localhost`-ot,
amikor az alkalmazást közvetlenül a hoszton futtatja egy Dockerizált vagy helyi Postgres ellen.
