# Development and architecture guide

This guide records the collaboration practices, service boundaries, and design work for Unified Retrieval System. It is tailored to the current codebase and its planned retrieval service; it does not imply that planned components already exist.

## Product description

Unified Retrieval System is intended to be a private, conversation-centered messaging and knowledge retrieval application. People exchange messages and media in explicit one-to-one conversations, then ask questions grounded in content they are allowed to access. Answers should link back to the originating message, attachment, PDF page, or audio/video timestamp, and say when available evidence is insufficient.

The current application is the messaging and shared-media foundation. Retrieval, ingestion workers, transcription, OCR, embeddings, reranking, and AI answer generation remain planned work. The long-term research goal is to compare keyword, dense, hybrid, and reranked retrieval on a versioned evaluation corpus, with reproducible quality and latency measurements.

## Collaboration and working rules

- Read this guide, the [project vision](project-vision.md), the [roadmap](plan.md), and relevant `AGENTS.md` files before editing.
- Work from the current `main` or explicitly designated integration branch. Create a focused `codex/<short-topic>` branch and keep changes reviewable.
- Make the smallest complete change that fits the product scope. Preserve existing user data and authorization boundaries; use additive database migrations where possible.
- Keep implementation, setup instructions, architecture docs, and the roadmap in sync. Mark planned work as planned and prototype behavior as prototype behavior.
- Run the build and relevant tests before proposing a change. Use synthetic fixtures and isolated, disposable databases for tests and retrieval experiments.
- Inspect the full diff and status before staging. Commit only project files, use clear commit messages, and submit feature work through a pull request for review.
- Never commit credentials, `.env` files, OTPs, private chat exports, attachments, local databases, Docker volumes, model weights, or generated evaluation data containing private content.
- Review security, retention, failure, and retry behavior whenever a change touches messages, uploads, processing, or retrieval. Details are in [CONTRIBUTING.md](../CONTRIBUTING.md).

## Current architecture and data flow

### Implemented prototype

```text
Next.js web client
  ├── HTTP requests and uploads ──► NestJS API
  └── WebSocket refresh notices ──► NestJS API
                                      ├── PostgreSQL + pgvector image
                                      │   durable users, sessions, contacts,
                                      │   conversations, messages, attachments
                                      └── Redis
                                          realtime coordination / ephemeral state
```

Docker Compose runs the web app, API, PostgreSQL, and Redis for local development. PostgreSQL is the durable source of truth; realtime notices prompt clients to refresh persisted state. The current prototype supports phone-based development OTP, one-to-one conversations, text messages, and membership-checked image, audio, video, PDF, and link views. The existing attachment constraints and retention behavior are documented in the [README](../README.md).

### Planned retrieval path

```text
Authorized conversation messages and attachments
  → durable processing job
  → format-specific extraction (PDF text, audio transcription,
    video audio extraction; later scoped OCR where designed)
  → source-linked canonical chunks and derived artifacts
  → conversation-authorized keyword / dense / hybrid retrieval
  → optional reranking
  → grounded answer with inspectable source citations
  → versioned offline evaluation
```

The processing worker and retrieval API are not implemented yet. The roadmap defines their intended sequence. Keep normal messaging available when asynchronous processing or retrieval is unavailable.

## Implementation boundaries

For changes to the current prototype, the usual path is:

1. **Web UI (`apps/web`)**: collect and render user interactions; do not treat client-supplied IDs as authorization.
2. **API (`apps/api`)**: validate requests, authenticate users, authorize conversation membership, and expose stable responses.
3. **Persistence (`db/migrations`)**: use additive, reviewable SQL migrations for durable schema changes; PostgreSQL owns durable application data.
4. **Realtime and cache (`Redis`)**: use for coordination or ephemeral state, not as the sole source of a message or retrieval record.

For future ingestion and retrieval, keep extraction, indexing, and answer generation in separately observable service boundaries. Persist job state and retries, version processors and models, and retain a source reference for every chunk and answer citation.

## Required design artifacts

Create or update these as the corresponding work begins:

- Use-case diagram for user, conversation, media processing, retrieval, and administrative actors.
- Logical architecture diagram showing web, API, database, realtime, worker, and retrieval boundaries.
- Deployment/development view covering local Docker services, ports, configuration, storage paths, and later deployment assumptions.
- Relational schema and migration notes for users, sessions, contacts, conversations, messages, attachments, processing jobs, chunks, and evaluation records as those entities are added.
- API contracts for authentication, conversations, media, processing, search, and answers, including authorization, payloads, errors, and retry semantics.
- Reproducible retrieval evaluation protocol recording dataset/split, model and processor versions, configuration, latency, and retrieval metrics.

Do not document a planned artifact as complete until the file exists and matches the running system.
