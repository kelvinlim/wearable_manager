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
- **2026-04-26** — Per-study Google Health API credentials with Fernet-encrypted secrets ([DESIGN.md](DESIGN.md) decisions 3 + 14).
  - Four columns added to `studies`: `google_oauth_client_id` (text), `google_oauth_client_secret` (Fernet-encrypted text), `google_cloud_project_id` (text), `webhook_authorization_value` (Fernet-encrypted text). Migration: [backend/alembic/versions/6efa85cd7de2_studies_per_pi_google_oauth_client_.py](backend/alembic/versions/6efa85cd7de2_studies_per_pi_google_oauth_client_.py).
  - [backend/app/services/crypto.py](backend/app/services/crypto.py): `EncryptedText` SQLAlchemy `TypeDecorator` (transparent encrypt-on-bind, decrypt-on-result) plus `encrypt_str` / `decrypt_str` helpers. Key from `STUDY_CREDS_KEY` env (Fernet 32-byte url-safe base64).
  - [backend/app/services/oauth_config.py](backend/app/services/oauth_config.py): `resolve_participant_oauth_config(study)` returns a `ParticipantOAuthConfig` dataclass tagged `source="study"` (per-study columns) or `source="fallback"` (env: `PARTICIPANT_GOOGLE_CLIENT_ID/SECRET`, `PARTICIPANT_GOOGLE_CLOUD_PROJECT_ID`, `WEBHOOK_SECRET`). Returns `None` when neither is fully configured.
  - Smoke-tested: ORM round-trip stores Fernet ciphertext (`gAAAA…`) on disk, decrypts to plaintext on read; resolver tags `source=study` correctly.

### Decisions

- **Container runtime** — Podman (rootful) over Docker. No daemon, native systemd integration via Quadlet, already available on RHEL 9.
- **Postgres version** — 16. Current stable line at project start; supported until November 2028.
- **Node version** — 24 (active LTS, supported until April 2028). Considered 22 (Apr 2027 EOL) for max stability but went current since the project is greenfield.
- **Per-study participant OAuth client** — Each PI brings their own Google Cloud project + OAuth client, stored on the `studies` row; an app-wide env fallback (`PARTICIPANT_GOOGLE_*` + `WEBHOOK_SECRET`) covers studies that haven't onboarded their own. Webhook discrimination via `clientProvidedSubscriptionName = "study-<id>-user-<healthUserId>"`. Operational cost: each PI independently runs OAuth verification (multi-week). See [DESIGN.md](DESIGN.md) decision 3 for full rationale.
- **Fernet for credential encryption at rest** — `studies.google_oauth_client_secret` and `studies.webhook_authorization_value` are Fernet-encrypted via a transparent SQLAlchemy `TypeDecorator`. Key in `STUDY_CREDS_KEY`; loss of the key bricks every encrypted credential. Cloud KMS rejected as overkill at this scale; plaintext rejected because one DB read would leak every PI at once. Participant OAuth tokens on `participants` remain plaintext for now (separate followup, lower per-row stakes). See [DESIGN.md](DESIGN.md) decision 14.

### Notes

- `authlib.jose` (used in [backend/app/services/jwt_auth.py](backend/app/services/jwt_auth.py)) emits a deprecation warning on import — authlib recommends `joserfc` for new code. Cheap swap; deferred.
- Postgres password lives in `/home/kolim/Projects/wearable_manager/.env.db` (gitignored) and is interpolated into [backend/.env](backend/.env) (also gitignored). The container's `wearable_manager` database was created via `sudo podman exec postgres16 createdb -U postgres wearable_manager`.
- A `STUDY_CREDS_KEY` was generated and added to [backend/.env](backend/.env) on 2026-04-26. **Back this key up off-host** — losing it bricks every Fernet-encrypted column in the DB. Rotation path: `MultiFernet([new, old])`, deferred until needed.

### Up next

**Restart point:** [DESIGN.md](DESIGN.md) §"Build phasing" Phase 2 — studies + participants CRUD with `entry_code` auto-gen (2 letters + 1 digit + 2 letters, ported from [garmin_django/](garmin_django/)), per-study scoping enforced on every endpoint (mirror `get_queryset` override pattern). The per-study OAuth credential columns (decision 3) should be exposed in the studies form so PIs can populate them at study-create time.

Pre-requisites that block end-to-end auth but not Phase 2 coding:
- Provision OAuth client #1 (researcher web app) in Google Cloud per [DESIGN.md](DESIGN.md) §"Cloud / ops prereqs"; populate `RESEARCHER_GOOGLE_CLIENT_ID` / `RESEARCHER_GOOGLE_CLIENT_SECRET` in [backend/.env](backend/.env).
- Add `<host>/wearablemgr/auth/google/callback` (or `http://127.0.0.1:8000/auth/google/callback` for local dev) to that client's authorized redirect URIs.
- *(Optional, only if running app-wide fallback mode)* Provision the participant Google Cloud project + OAuth client + verification; populate `PARTICIPANT_GOOGLE_*` + `WEBHOOK_SECRET` in [backend/.env](backend/.env).
