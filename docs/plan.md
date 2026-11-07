# Implementation plan

1. **Messaging foundation (prototype):** PostgreSQL-backed phone verification, explicit sessions, mutual contacts, durable idempotent messages, and reconnect synchronization.
2. **Initial attachments (prototype):** private membership-checked media, file, and link views; 20 MiB uploads; additive migration; 30-day attachment byte expiration. Full backup deletion, malware scanning, object storage, and browser end-to-end coverage remain open.
3. **Processing foundation:** define the canonical evidence contract, durable processing jobs, retries, and retention for all derived artifacts.
4. **Ingestion:** extract PDF text with page references, transcribe audio, and extract audio from video while retaining timestamps. Keep ordinary messaging available when workers fail.
5. **Authorized retrieval:** establish a keyword baseline, then add dense retrieval, reranking, and optional hybrid fusion with membership filtering before results are returned.
6. **Grounded answers:** add optional local generation only after citations can be verified against retrieved evidence.
7. **Evaluation and operations:** add a versioned synthetic/consented corpus, reproducible metrics, performance and failure tests, security review, and recovery documentation.

## Design and delivery checklist

Keep this checklist current as work lands. The architecture, layer boundaries, and intended data flows are described in the [development guide](development-guide.md).

### Architecture and API

- [ ] Add a use-case view for users, conversations, media processing, retrieval, and operations.
- [ ] Add logical and deployment views that match the actual web, API, database, realtime, and planned worker services.
- [ ] Document the relational schema and relationships, including processing jobs, source-linked chunks, and evaluation records when introduced.
- [ ] Publish API contracts for authentication, contacts/conversations, messages, attachments, processing, search, and answers, including payloads, errors, access checks, and retry behavior.

### Product capabilities

- [ ] Add user profile read/update and account deletion flows with session revocation and data-retention behavior.
- [ ] Decide and implement message edit, delete, and reply behavior, including how changes affect derived retrieval evidence.
- [ ] Add attachment deletion and metadata management with cleanup of derived artifacts, caches, and retained copies.
- [ ] Build durable asynchronous ingestion for PDF pages, audio transcription, and video audio tracks with source offsets, retries, and observable failures.
- [ ] Establish an authorized keyword-search baseline before adding dense, hybrid, or reranked retrieval.
- [ ] Add grounded answers that cite source messages, PDF pages, and media timestamps and decline when evidence is insufficient.
- [ ] Build a versioned evaluation set and report retrieval quality, attribution accuracy, and latency separately from answer quality.

### Release readiness

- [ ] Add browser-level end-to-end coverage for sign-in, two-user messaging, media sharing, and conversation access controls.
- [ ] Define malware scanning, backup/restore, object storage, and complete source-plus-derived data retention before production use.
- [ ] Replace development OTP and secrets with production identity, configuration, and deployment procedures before public deployment.

## Decisions

- This is a local development project. The first increment uses a development-only OTP provider; production must integrate a real provider and deployment secrets.
- Opaque session tokens are stored as hashes in PostgreSQL and sent as HTTP-only cookies. Registration and sign-in are separate verifications.
- A contact request returns the same response whether a number exists or not. A conversation can only be created after both users have added each other. This avoids returning a directory of registered users.
- PostgreSQL is the durable source of truth. Socket events are notifications; clients reload persisted messages on connection and reconnect.
- The interface explicitly states that server-side processing is possible and there is no end-to-end encryption.
- Reading this as: a messaging workspace for people who need to recover shared information, in a quiet editorial style, ENERGY 1 / RHYTHM 1 / MOTION 1. Muted ink and warm paper keep conversation content legible; teal identifies the active action. System sans type is dependable at small sizes. Borders divide working areas instead of decorative cards. No illustration or animation competes with messages.
