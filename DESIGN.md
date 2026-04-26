# wearable_manager — Design

Working design document for the new wearable_manager app. Captures decisions made on 2026-04-26 and the Health Migration API facts those decisions rest on. Update this file when decisions change; don't let it drift.

## Purpose

Web app that registers participants for Fitbit (and later Garmin) data sharing and ingests their daily data via webhook. One JSON payload per `(participant, date, source)`. See [README.md](README.md) for the project brief.

The app replaces what is currently split across two reference projects:
- [fitbitreg/](fitbitreg/) — Flask + SQLAlchemy participant-registration flow against the legacy Fitbit Web API
- [garmin_django/](garmin_django/) — Django admin app managing studies, participants, ingested data

Neither is being modified. They are kept as references; their CLAUDE.md files document non-obvious behavior worth porting.

## Stack

- Backend: FastAPI, SQLAlchemy 2.0 async, asyncpg, Alembic (async template), authlib, httpx, pydantic-settings, Jinja2
- Frontend: Vite, React, TypeScript, TanStack Query, orval (OpenAPI codegen), Tailwind, shadcn/ui
- Infra: Postgres, no Redis until justified. Worker is a sibling asyncio process in the same Python package — not a separate service.
- Tests: pytest, pytest-asyncio, httpx.AsyncClient, ephemeral Postgres (testcontainers or pytest-postgresql).

## Locked-in decisions

Each decision lists the rejected alternative and why this one won, so edge cases can be judged later.

1. **Both vendors (Fitbit + Garmin) supported in the data model from day one.**
   `daily_data.source` column distinguishes them. Worker dispatches by source. Garmin code stubbed until needed. Rejected: Fitbit-only schema and refactor later — cheap to do now, painful retrofit.

2. **Server-rendered FastAPI page for participant enrollment at `/enroll/{code}`.**
   Jinja templates. SPA owns the rest. Rejected: SPA route for enrollment — added CORS + SPA-handled OAuth callback complexity for a one-shot URL.

3. **Two separate Google OAuth clients.**
   One for researcher OIDC sign-in (`openid email profile`), one for participant Health Migration data sharing (`googlehealth.*`). Rejected: single combined client — mixes identity and data-access scopes in one consent.

4. **Deployed on UMN intranet behind nginx under a path prefix.**
   FastAPI `root_path` driven by `APP_PATH` env (default `/wearablemgr/`), `ProxyHeadersMiddleware` for correct redirect URLs. Same pattern as fitbitreg's `APP_PATH` and garmin_django's `appname`.

5. **Researcher UI v1 = minimal CRUD + per-day raw-data viewer.**
   Studies list/detail, participants list/detail, enrollment status, manual data-pull trigger, raw daily JSON viewer on the participant detail page. No charts library. Rejected: full charted dashboard — the SDD's direction, deferred to v2.

6. **Researchers are pre-provisioned by an admin; no self-onboarding.**
   Sign-in via Google OIDC, but access is granted only if the email already exists in `users`. Rejected: any-Google-account-with-domain-restriction.

7. **Single superadmin via `ADMIN_EMAIL` env.**
   Email matches on first sign-in → `role='admin'`. Admin adds researchers in the UI. Rejected: in-app admin promotion — defer until needed.

8. **`APP_PATH` env, default `/wearablemgr/`.**
   Configurable per environment, same as fitbitreg.

9. **Raw JSON only in `daily_data`, extract on read.**
   Schema: `(participant_id, date, source, payload jsonb, fetched_at)` UNIQUE on the triple. Mirrors garmin_django's `Garmindata.d` pattern. GIN index only if a query justifies it. Rejected: denormalized columns for common metrics — schema migration cost every time researchers want a new metric.

10. **No backfill on registration — forward-only from first notification.**
    Avoids burning API budget on enrollment day. Researcher knows data starts at registration. (Recovery from worker downtime > 7 days is a separate ad-hoc fetch path, not backfill.)

11. **On notification, refetch the whole day, debounced.**
    Default debounce window 10 min on `(healthUserId, date)`. Single upsert per day. Rejected: per-collection merge — more code for marginal API savings.

12. **MANUAL subscription policy.**
    Worker calls `CreateSubscription` per data type per user after OAuth callback; `DeleteSubscription` on revoke. Rejected: AUTOMATIC — currently covers only `altitude / distance / floors / sleep / steps / weight`, missing heart rate / HRV which are core to several lab studies.

13. **Build now against the GA API; accept churn.**
    Stay in test-user mode (≤100 users) until OAuth verification clears. Keep the Health API integration thin and isolated in `services/health_*.py` + `workers/ingest.py` so a breaking change is patched in one layer.

## Health Migration API facts that shaped the design

Source: https://developers.google.com/health/migration (researched 2026-04-26). Re-verify before relying — the API was GA on 2026-03-24 and Google recommended waiting until end of May 2026 for production launches.

- **OAuth.** Standard Google OAuth at `accounts.google.com/o/oauth2/v2/auth`, tokens at `oauth2.googleapis.com/token`. Scopes are coarse-by-domain under `https://www.googleapis.com/auth/googlehealth.*` (e.g. `activity_and_fitness`, `sleep`, `heart_rate` — each with `.readonly` variant). Access tokens last 1 hour; refresh tokens issued, expire after 6 months unused.
- **Participants must have a Google account.** Fitbit-only login no longer exists post-migration. Existing Fitbit tokens are not portable — re-consent required.
- **Webhooks are push-with-trigger.** Notification body has `(healthUserId, dataType, operation [UPSERT|DELETE], intervals, clientProvidedSubscriptionName)`. The actual data must be fetched.
- **Webhook auth = static `Authorization` header.** App provides the literal header value at subscriber registration; Google echoes it on every notification. Not HMAC-SHA1 (legacy Fitbit), not JWT, not mTLS. Stored as `WEBHOOK_SECRET` env. There is also possibly an `X-HEALTHAPI-SIGNATURE` ECDSA P-256 signature mentioned on one doc page — verify against a test subscriber before depending on either.
- **Webhook must return 204 immediately.** Non-2xx or timeout → exponential-backoff retries for up to 7 days, then dropped. Handler must be idempotent on `(healthUserId, dataType, intervals)`.
- **Subscription registration is project-level.** `POST https://health.googleapis.com/v4/projects/{project}/subscribers` registers the single webhook endpoint for the whole app. Requires `cloud-platform` OAuth scope and `health.subscribers.create` IAM. Two-step verification handshake at registration: probe with the configured `Authorization` header must return 200/201; probe without auth must return 401/403. User-Agent on probe is `Google-Health-API-Webhooks-Verifier`.
- **Per-user subscriptions are required under MANUAL policy.** App calls `CreateSubscription` per `(user, data type)` after OAuth. AUTOMATIC policy would compute eligibility from consent but currently covers a subset of data types (see decision 12).
- **Data fetch.** No "give me the whole day" endpoint. Fan out per data type via `GET /v4/{parent=users/*/dataTypes/*}/dataPoints` (also `:rollUp`, `:dailyRollUp`, `:reconcile`, `:exportExerciseTcx`). The notification's `dataType` + `intervals` says what to refetch.
- **Rate limits.** Not documented publicly. Legacy 150 req/hour/user is not restated. Plan to monitor 429s. The OAuth 100-user limit for unverified clients is real and gates a production launch.
- **Notifications expire after 7 days.** Worker downtime longer than that = data permanently lost from the queue. Recovery path: an ad-hoc "fetch days N..M for participant P" endpoint backed by `dataPoints` queries. Not part of v1 happy path.

## Data model

```
users(
  id, email unique, name,
  role enum[admin, researcher],
  created_at
)

studies(
  id, name, wearable_type_id,
  owner_user_id fk users,
  created_at
)

study_members(study_id, user_id, role)        -- M2M, per-study scoping enforced on every endpoint

wearable_types(id, name)                       -- 'fitbit', 'garmin'

participants(
  id, study_id fk, wearable_type_id fk,
  entry_code unique,                           -- 2 letters + 1 digit + 2 letters, ported from garmin_django
  status enum[pending, registered, revoked],
  google_health_user_id,                       -- the API's healthUserId
  oauth_access_token, oauth_refresh_token,
  oauth_scopes, oauth_expires_at,
  registered_at
)

oauth_state(
  state pk, code_verifier,
  participant_id fk, created_at                -- short-lived, replaces fitbitreg's module globals
)

daily_data(
  id, participant_id fk, date, source,         -- 'fitbit' | 'garmin'
  payload jsonb,                               -- {data_type: [...], ...}
  fetched_at,
  UNIQUE(participant_id, date, source)
)

notification_queue(
  id, google_health_user_id, data_type,
  operation, interval_start, interval_end,
  received_at, processed_at,
  attempts, last_error
)
```

Per-study scoping: every API endpoint that returns participant or daily-data rows filters by `study_members` for non-admin users. Mirrors garmin_django's `get_queryset` override pattern.

## Flows

### Researcher login

1. React "Sign in with Google" → OAuth client #1 (researcher) → OIDC code flow handled by `authlib`.
2. Backend looks up email in `users`. Absent → reject. Present → mint JWT, set HttpOnly cookie.
3. Admin role gates the "add researcher" UI and any cross-study views.

### Participant enrollment

1. `GET /enroll/{code}` (Jinja). Validates `entry_code`, shows consent copy + "Connect Fitbit" button.
2. `POST /enroll/oauth/start` mints PKCE+state, persists `oauth_state` row, redirects to `accounts.google.com/o/oauth2/v2/auth` with the chosen `googlehealth.*` scopes (OAuth client #2 — participant).
3. `GET /enroll/oauth/callback` validates state from DB, exchanges code, stores tokens + `google_health_user_id` on the `participants` row, marks `status=registered`.
4. After token storage, the callback (or a fast-path background task) calls `CreateSubscription` once per data type for this user (MANUAL policy).
5. Revocation notification → `DeleteSubscription` for any remaining per-user subs, clear tokens, set `status=revoked`.

### Webhook

1. `POST /webhook` — validate `Authorization` header against `WEBHOOK_SECRET`, optionally ECDSA-verify `X-HEALTHAPI-SIGNATURE` once confirmed. INSERT one row per notification entry into `notification_queue`. Return `204` immediately.
2. Verification handshake — handle the two-probe sequence per the API spec. Idempotent: re-running subscriber registration must not break the live webhook.

### Worker

1. Polls `notification_queue` for unprocessed rows.
2. Groups by `(google_health_user_id, date_from(intervals))` over a 10-min debounce window.
3. Resolves to `participant_id`. Refreshes OAuth token if `oauth_expires_at` is near.
4. For each data type in the group, calls `users/{health_id}/dataTypes/{type}/dataPoints` for the affected intervals.
5. Merges results into a single `payload` dict keyed by data type, `INSERT ... ON CONFLICT (participant_id, date, source) DO UPDATE`.
6. Marks queue rows processed. Dead-letters after N attempts with `last_error`.

## Anti-drift mechanism (the reason this is one codebase)

Backend Pydantic schemas are the source of truth. `make codegen`:
1. Boots the FastAPI app, dumps OpenAPI to `shared/openapi/openapi.json`.
2. Runs `orval` to regenerate `frontend/src/api/` (typed React Query hooks + types).

CI gate: `make codegen` must produce no diff. A schema change without a regenerated client fails CI. This is the lever — DB → API → UI types stay aligned automatically; researchers and ingestion never read different shapes.

## Repo layout

```
wearable_manager/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI, root_path from APP_PATH
│   │   ├── config.py              # pydantic-settings
│   │   ├── db.py                  # async engine, AsyncSession
│   │   ├── models/                # SQLAlchemy 2.0
│   │   ├── schemas/               # Pydantic
│   │   ├── api/                   # researcher API routers
│   │   │   ├── auth_google.py
│   │   │   ├── studies.py
│   │   │   ├── participants.py
│   │   │   └── data.py
│   │   ├── enroll/                # server-rendered participant flow
│   │   │   ├── routes.py
│   │   │   └── templates/
│   │   ├── webhook/
│   │   │   └── routes.py
│   │   ├── services/
│   │   │   ├── google_oauth.py    # researcher OIDC
│   │   │   ├── health_oauth.py    # participant Health Migration OAuth
│   │   │   ├── health_client.py   # async client + token refresh
│   │   │   └── subscriber.py      # projects.subscribers + per-user subs
│   │   └── workers/
│   │       └── ingest.py
│   ├── alembic/
│   ├── pyproject.toml
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── api/                   # generated — do not edit
│   │   ├── pages/
│   │   └── components/
│   ├── package.json
│   └── vite.config.ts
├── shared/openapi/                # checked-in OpenAPI snapshot
├── compose.yaml                   # api, worker, postgres
├── Dockerfile
├── Makefile                       # codegen, dev, test, migrate, subscriber-create
├── DESIGN.md
├── CLAUDE.md
└── README.md
```

## Cloud / ops prereqs

These are real blockers, not implementation details. Track separately from code work.

1. Google Cloud project; enable Health API.
2. OAuth consent screen — scopes for both flows.
3. Two OAuth client IDs (researcher web app + participant web app).
4. Test-user emails added until verified (≤100 users limit).
5. Apply for OAuth verification — third-party security review; multi-week.
6. Provision `WEBHOOK_SECRET`.
7. Run subscriber-create once webhook URL is live behind nginx (HTTPS only).
8. UMN nginx route + cert for `/wearablemgr/webhook` and `/wearablemgr/enroll/*`.

## Build phasing

1. Repo skeleton, Postgres + Alembic, models, FastAPI scaffold with `root_path=APP_PATH`, researcher Google OIDC, admin bootstrap from `ADMIN_EMAIL`.
2. Studies + participants CRUD; entry_code auto-gen.
3. Server-rendered enrollment flow with mocked Health OAuth.
4. Real Health OAuth + token storage; smoke-test against Google's OAuth Playground.
5. `/webhook` handler + `notification_queue` + verification handshake; `subscriber-create` CLI.
6. Worker: data-type fan-out, daily upsert, debounce, token refresh, dead-letter.
7. Per-user MANUAL subscribe on enrollment callback; unsubscribe on revoke.
8. Frontend MVP: studies list, participant list, participant detail with raw daily JSON viewer.
9. Codegen wiring + CI gate on OpenAPI snapshot.
10. Garmin-shaped no-op stubs (worker dispatches by source) so the schema is exercised.

## Open questions / things to verify on first contact

These are intentional gaps — verify against the live API before writing code that depends on them, and update this section when answered.

- **Webhook signature.** Is the `Authorization` header sufficient, or is `X-HEALTHAPI-SIGNATURE` (ECDSA P-256) also required / recommended? Test subscriber should reveal this.
- **Rate limits.** Empirical — instrument 429 responses in the worker from day one.
- **AUTOMATIC data-type coverage** if we ever want to switch — re-check the supported list.
- **Refresh-token expiry behavior** under `Testing` vs verified consent screens — affects how aggressively we reauth participants pre-launch.
- **`CreateSubscription` payload** — exact body, idempotency semantics, behavior on duplicate creation.
- **Bulk `dataPoints` query** — confirm whether multiple `intervals` can be queried in one call or if we have to issue one per interval.
