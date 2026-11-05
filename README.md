# Commonplace: messaging foundation

This repository is an **incomplete local-development increment** toward the application described in the brief. It is not production-ready and does not yet deliver multimodal retrieval. Do not use it for private or sensitive conversations.

## What is implemented

- A Next.js interface for registration, sign-in, mutual contacts, and one-to-one text conversations.
- A NestJS API with development-only phone codes, E.164 validation, hashed opaque session tokens, rate limits, and logout.
- PostgreSQL tables and a first SQL migration for identity, contacts, conversations, messages, and receipts. PostgreSQL stores the durable messages; Socket.IO notifies clients to reload, including on reconnect. Messages have client-generated idempotency keys and cursor pagination.
- A local Compose definition for PostgreSQL, Redis, API, and web. The OTP provider prints verification codes and phone numbers in API logs, so it must only be used with disposable development data. The API deliberately refuses to start in production mode.

The two participants must each add the other's phone number before a conversation is shown. This is a conservative privacy choice for the prototype. Adding a contact does not report whether that number is registered. Registration verification does not sign a user in: request a second code for sign-in.

## Start locally

Requirements: Docker with the Compose plugin, and ports 3000, 3001, 55433, and 6379 available on localhost. PostgreSQL and Redis store their development data under `DockerData/` in the project directory; do not delete these directories if you need the data. PostgreSQL is exposed locally on port 55433 to avoid conflicting with a local PostgreSQL server.

```sh
docker compose up --build
```

Open `http://localhost:3000`. Request a verification code and find it in `docker compose logs api`. Register two disposable accounts, sign in separately, and have each add the other's number. The migration runs when the PostgreSQL volume is first initialized. Existing volumes are not automatically migrated; a proper migration runner remains to be implemented.

For frontend or API development outside Compose, install Node.js 22 or later and run `npm ci`. Start PostgreSQL and Redis, apply `db/migrations/001_foundation.sql` to a dedicated database, then set `DATABASE_URL`, `REDIS_URL`, `OTP_SECRET` (at least 24 characters), and `WEB_ORIGIN`. Use `npm run dev:api` and `npm run dev:web` in separate terminals. The API dev command compiles once before starting; restart it after changes.

Run `npm run build`, `npm test`, and `npm audit --omit=dev` for the available checks. For the PostgreSQL-backed verification concurrency test, set `TEST_DATABASE_URL` to a dedicated disposable PostgreSQL database before running `npm test`. The test creates and removes an isolated schema. Without this variable the database test is skipped. These checks do not yet prove the full authentication, socket, or UI flows.

## Important gaps

Phase 1 is not complete or verified end to end. There is no production SMS provider, session rotation or management, account recovery or deletion, blocking or reporting, presence, typing, message edit/delete/reply, or separate delivery receipt. The message list uses pagination but is not virtualized. Connection changes, retries, race conditions, authorization, and abuse resistance need integration and end-to-end tests. The development OTP provider and hard-coded Compose database credentials are not suitable for deployment.

Media uploads, private object storage, media validation and processing, 30-day expiration, retrieval and search, embeddings, reranking, answer generation, citations, summarization, research evaluation, performance tests, observability, and a security review are not implemented. No 30-day deletion guarantee exists in this increment. Text messages have no automatic retention limit, and the deletion control is not yet implemented.

The server can read message contents. **End-to-end encryption is not implemented.** There is no malware scanning, backup deletion policy, or production secrets management. Backups, operational logs, and legal retention requirements will need explicit policies before real data is accepted. See [the plan](docs/plan.md) for the intended order and decisions.
