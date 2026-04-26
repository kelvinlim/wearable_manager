## CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

Greenfield. The repo currently contains only [README.md](README.md), [DESIGN.md](DESIGN.md), and symlinks to three reference projects ([fitbitreg/](fitbitreg/), [garmin_django/](garmin_django/), [garminrec/](garminrec/)). There is no application code, package manifest, build, lint, test, or CI yet — do not invent commands. The first implementation steps still need to be scaffolded.

**Read [DESIGN.md](DESIGN.md) before proposing or writing code.** It captures the locked-in architecture decisions, the Health Migration API facts they rest on, the data model, the flows, and the build phasing. Decisions there are the result of an explicit Q&A and shouldn't be relitigated without checking with the user.

## What this project is

A new web application that registers users for Fitbit and Garmin wearables and ingests their data via subscription/webhook. Per [README.md](README.md):

- **One JSON payload per user per day** is the intended storage shape for ingested data.
- **Fitbit first**, using Google's Health Migration API: https://developers.google.com/health/migration. This is the post-platform-migration successor to the standalone Fitbit Web API the reference [fitbitreg/](fitbitreg/) app targets — auth, scopes, subscription mechanics, and rate-limit semantics are different, so port behavior (registration UX, per-day storage shape, debounce) rather than copying the Fitbit Web API call patterns.
- Garmin to follow.

## Target architecture (from README)

- **Backend:** FastAPI
- **DB:** Postgres + SQLAlchemy 2.0 **async** + Alembic migrations
- **Frontend:** React
- **Auth:** Google Sign-In (OAuth2 / OIDC)

This is a deliberate departure from the reference projects (Flask + MySQL for `fitbitreg`, Django + MySQL for `garmin_django`). When porting logic, port the *behavior*, not the framework idioms — translate Django ORM / Flask routes into async SQLAlchemy + FastAPI rather than mirroring them.

## The three reference folders

These are symlinked siblings, not part of this app. Each has its own git repo and CLAUDE.md. Read those CLAUDE.md files before pulling code from them — they document non-obvious schema co-tenancy and bootstrap quirks.

- **[fitbitreg/](fitbitreg/)** — Flask + SQLAlchemy app for Fitbit OAuth2 + PKCE registration. Closest analog to the registration flow this app needs to replicate. See [fitbitreg/CLAUDE.md](fitbitreg/CLAUDE.md) and [fitbitreg/FitbitSubscription.md](fitbitreg/FitbitSubscription.md) — the latter is the working design doc for Fitbit subscriptions/webhooks (one row per `(subject, day)`, 3-second webhook deadline, HMAC-SHA1 signature verification, queue+worker pattern, debouncing for the 150 calls/hour rate limit). Most of those concerns carry over.
- **[garmin_django/](garmin_django/)** — Django admin app managing studies, subject `Accounts`, and ingested `Garmindata` (raw JSON keyed by `datatype`). Useful for: data model shape (`Wearable` → `Study` → `Accounts` → `Garmindata`), the per-study scoping rule (non-superusers see only studies they belong to via `Study.users` M2M), the `entry_code` auto-generation pattern (2 letters + 1 digit + 2 letters), and the `streamdata` canonical export format (see [garmin_django/CLAUDE.md](garmin_django/CLAUDE.md) and [garmin_django/SDD_Migration_React_FastAPI.md](garmin_django/SDD_Migration_React_FastAPI.md), which sketches a similar React/FastAPI migration but keeps MySQL — this project uses Postgres instead).
- **[garminrec/](garminrec/)** — older experimental code; lowest signal of the three.

## Things to confirm before writing code

The README is short and several specifics are unstated. Before scaffolding, surface these to the user rather than guessing:

1. **Health Migration API specifics.** The reference [fitbitreg/FitbitSubscription.md](fitbitreg/FitbitSubscription.md) describes the *legacy* Fitbit subscription model (POST per collection, trigger-only notifications, 3s deadline, HMAC-SHA1 with client secret, dev-portal-configured subscriber type). The Google Health Migration API may differ on every one of those points. Verify against https://developers.google.com/health/migration before assuming carryover.
2. **Schema continuity vs. fresh start.** The reference apps share `accounts` / `garmindata` MySQL tables with external ingestion. This project specifies Postgres, so it is presumably a clean schema — confirm rather than mechanically translating the existing one.
3. **Worker model.** [fitbitreg/FitbitSubscription.md](fitbitreg/FitbitSubscription.md) leaves the queue-vs-thread choice open. FastAPI gives both options (BackgroundTasks vs. Celery/RQ + Redis); pick deliberately, not by default.
