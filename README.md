# FPL Assistant

A private, single-user Fantasy Premier League planning app, designed for Docker on a local computer and eventually an Ubuntu VM on Proxmox.

**Milestone 1 is implemented:** a FastAPI API, React interface, SQLite migrations, persistent workspace notes, a health check, and entirely fictional demonstration data. No FPL login, API keys, external data requests, or upstream team changes are involved.

## Run locally

Start Docker Desktop, then run from this repository:

```sh
docker compose up --build -d --wait app
```

Open **http://localhost:8000**. The service binds to `127.0.0.1` only. Optional `.env` setting `APP_PORT=8001` changes the host port if 8000 is in use. No `.env` file is needed with the defaults.

On this Mac, if `docker` is not on PATH, use the following for the current Terminal session:

```sh
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
```

## What works

- A 15-player demo squad in pitch and list views, with captain, vice-captain, and ordered bench.
- A searchable 20-player fictional catalogue with position filters and price sorting.
- Player details showing current price and, for squad members, individual purchase and selling prices.
- An editable workspace name and planning notes, saved in SQLite and retained across restarts and container replacement.
- Automatic Alembic migrations and an idempotent demo seed.
- A responsive interface with keyboard-accessible controls, dialog focus handling, and unsaved-note protection.

The sample season/gameweek, clubs, players, prices, and fixtures are illustrative, not live FPL information. Prices use integer units of £0.1 million. Dates are stored in UTC and shown in the browser's timezone.

**Not implemented yet:** file imports, manual squad/budget corrections, transfer drafts, lineup changes, prediction/optimisation, authentication, or server deployment. The demo lineup is read only. Workspace notes are not a transfer draft.

## Verify

```sh
docker compose --profile test run --build --rm test
curl --fail http://localhost:8000/api/health
docker compose ps
```

The test container has no network access and uses temporary databases. Tests cover migrations/schema agreement, seeding, demo integrity, search, input validation, cross-origin write rejection, database failures, static serving, and persistence across new app instances. TypeScript checking and the production frontend build run during the image build.

See [the milestone 1 verification record](docs/VERIFICATION.md) for the checks completed on this Mac and their limits.

To check the actual data volume, save a note in the browser, run `docker compose restart app`, reload the page, and verify the note is still present. `docker compose down` removes containers while preserving data. **Do not use `docker compose down -v` unless you intend to delete the saved workspace.**

## Storage and operation

Docker Compose manages the named volume `fpl-assistant_app_data`, mounted at `/data`. The SQLite file is `/data/fpl-assistant.sqlite3`. The distroless Python runtime runs as UID/GID 10001 with a read-only root filesystem, a writable data volume, and a temporary `/tmp` directory. One worker runs migrations and seed initialization before serving requests. Build and test tools remain in separate stages; the shipped image has no shell, pip or general-purpose system utilities. Use `/usr/bin/python3` for container diagnostics.

```sh
docker compose logs --tail=100 app
docker compose stop app
docker compose up -d --wait app
```

- Health: `/api/health` (queries the database and migration revision; returns HTTP 503 when unavailable).
- API documentation: `/api/docs`.
- Overview: `GET /api/overview`.
- Catalogue: `GET /api/players?position=MID&q=Brooks`.
- Workspace: `PUT /api/workspace` with JSON `name` and `notes`.

There is no authentication in this milestone. Keep the loopback binding. Remote access and backup/restore procedures will be completed before the server-deployment milestone.

## Development layout

```text
backend/app/               FastAPI, database models, schemas, synthetic seed
backend/alembic/           Versioned SQLite migrations
backend/tests/             API, migration, persistence and offline tests
frontend/src/              React/TypeScript interface
Dockerfile                Frontend build, backend test and runtime targets
compose.yaml              Local app volume, port binding and isolated tests
```

Production and test Python dependency versions are fully pinned in `backend/requirements*.txt`; `requirements.in` records the direct runtime version ranges. The frontend has exact direct versions and `package-lock.json`; Docker uses `npm ci`. All three base images are pinned by multi-architecture digest. See [container security and exceptions](docs/SECURITY.md) for the runtime design, scanner configuration, complete scan artifacts and how to review a specific vulnerability exception.

## Next milestones

1. Validated JSON snapshot imports and manual corrections.
2. Independent saved drafts with budget, transfer and lineup validation.
3. Explainable expected points and affordable transfer suggestions.
4. Ubuntu VM deployment, private access and verified backup restoration.

The [implementation brief](docs/IMPLEMENTATION_BRIEF.md) defines the complete scope. The [setup plan](docs/SETUP.md) describes the future VM and self-hosted secrets service. No secrets are required for the demo.
