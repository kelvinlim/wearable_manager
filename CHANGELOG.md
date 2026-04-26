# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The project is pre-1.0 and greenfield; entries describe build-out progress
toward the first usable version.

## [Unreleased]

### Added

- **2026-04-26** — [scripts/install-postgres16.sh](scripts/install-postgres16.sh): rootful Podman + Quadlet installer for PostgreSQL 16 on RHEL 9.
  - Image `docker.io/library/postgres:16`.
  - Bind-mount data dir at `/var/lib/pgdata`.
  - Listens on `127.0.0.1:5432` only (loopback).
  - Generated 32-char superuser password written to `/etc/wearable-manager/db.env` (mode 0640) and `/root/.pgpass` (mode 0600).
  - Managed via systemd unit `postgres16.service` generated from a Quadlet at `/etc/containers/systemd/postgres16.container`.
  - Healthcheck via `pg_isready`.
  - Rootful chosen over rootless because the host is a shared server with multiple admins; rootless ties the service lifecycle to a single user account.
- **2026-04-26** — [scripts/install-nodejs.sh](scripts/install-nodejs.sh): installs Node.js 24 / npm 11 from the RHEL 9 AppStream `nodejs:24/common` module stream. System-wide install so all admins share one Node; per-project version pinning will live in `.nvmrc` / `package.json` `engines` once the frontend scaffolds.
- **2026-04-26** — [backend/](backend/): FastAPI + SQLAlchemy 2.0 async + Alembic skeleton ([DESIGN.md](DESIGN.md) Phase 1).
  - Python 3.13 venv at [backend/.venv/](backend/.venv/) (gitignored); deps pinned via [backend/requirements.txt](backend/requirements.txt) + [backend/requirements-dev.txt](backend/requirements-dev.txt) and mirrored in [backend/pyproject.toml](backend/pyproject.toml).
  - Models for the eight tables in DESIGN.md §"Data model" under [backend/app/models/](backend/app/models/) (`users`, `wearable_types`, `studies`, `study_members`, `participants`, `oauth_state`, `daily_data`, `notification_queue`).
  - Initial Alembic migration generated and applied: [backend/alembic/versions/0b04934b8d3a_initial_schema.py](backend/alembic/versions/0b04934b8d3a_initial_schema.py). Async env.py at [backend/alembic/env.py](backend/alembic/env.py).
  - Researcher Google OIDC via authlib: `GET /auth/google/login`, `GET /auth/google/callback`, `POST /auth/logout`, `GET /auth/me` ([backend/app/api/auth_google.py](backend/app/api/auth_google.py)). JWT in HttpOnly cookie (`wm_auth`), HS256 over `SECRET_KEY`.
  - Admin bootstrap: first sign-in by `ADMIN_EMAIL` creates a `role=admin` user; non-admin emails are rejected unless pre-provisioned. See [backend/app/api/auth_google.py](backend/app/api/auth_google.py) `_resolve_user`.
  - `SessionMiddleware` (transient OAuth state) + `ProxyHeadersMiddleware` (correct redirect URLs behind nginx with `root_path=APP_PATH`) wired in [backend/app/main.py](backend/app/main.py).
  - Smoke-tested locally: `/healthz` → 200, `/auth/me` (no/bad/valid cookie) → 401/401/200, `/auth/logout` → 204, `/auth/google/login` → 503 (creds unset, expected), `/openapi.json` lists all five paths under server `/wearablemgr`.

### Decisions

- **Container runtime** — Podman (rootful) over Docker. No daemon, native systemd integration via Quadlet, already available on RHEL 9.
- **Postgres version** — 16. Current stable line at project start; supported until November 2028.
- **Node version** — 24 (active LTS, supported until April 2028). Considered 22 (Apr 2027 EOL) for max stability but went current since the project is greenfield.

### Notes

- `authlib.jose` (used in [backend/app/services/jwt_auth.py](backend/app/services/jwt_auth.py)) emits a deprecation warning on import — authlib recommends `joserfc` for new code. Cheap swap; deferred.
- Postgres password lives in `/home/kolim/Projects/wearable_manager/.env.db` (gitignored) and is interpolated into [backend/.env](backend/.env) (also gitignored). The container's `wearable_manager` database was created via `sudo podman exec postgres16 createdb -U postgres wearable_manager`.

### Up next

**Restart point:** [DESIGN.md](DESIGN.md) §"Build phasing" Phase 2 — studies + participants CRUD with `entry_code` auto-gen (2 letters + 1 digit + 2 letters, ported from [garmin_django/](garmin_django/)), per-study scoping enforced on every endpoint (mirror `get_queryset` override pattern).

Pre-requisites that block end-to-end auth but not Phase 2 coding:
- Provision OAuth client #1 (researcher web app) in Google Cloud per [DESIGN.md](DESIGN.md) §"Cloud / ops prereqs"; populate `RESEARCHER_GOOGLE_CLIENT_ID` / `RESEARCHER_GOOGLE_CLIENT_SECRET` in [backend/.env](backend/.env).
- Add `<host>/wearablemgr/auth/google/callback` (or `http://127.0.0.1:8000/auth/google/callback` for local dev) to that client's authorized redirect URIs.
