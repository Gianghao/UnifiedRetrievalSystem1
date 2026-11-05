# Implementation plan

1. Establish a PostgreSQL-backed messaging foundation with phone verification, explicit sessions, contacts, durable idempotent messages, and reconnect synchronization.
2. Add private media, background processing, and retention before exposing upload controls.
3. Add the common evidence contract, ingestion, authorized retrieval, and evaluation.
4. Add grounded answers only after evidence and citations can be verified.
5. Exercise the system under failure and load, and document operational limits.

## Decisions

- This is a local development project. The first increment uses a development-only OTP provider; production must integrate a real provider and deployment secrets.
- Opaque session tokens are stored as hashes in PostgreSQL and sent as HTTP-only cookies. Registration and sign-in are separate verifications.
- A contact request returns the same response whether a number exists or not. A conversation can only be created after both users have added each other. This avoids returning a directory of registered users.
- PostgreSQL is the durable source of truth. Socket events are notifications; clients reload persisted messages on connection and reconnect.
- The interface explicitly states that server-side processing is possible and there is no end-to-end encryption.
- Reading this as: a messaging workspace for people who need to recover shared information, in a quiet editorial style, ENERGY 1 / RHYTHM 1 / MOTION 1. Muted ink and warm paper keep conversation content legible; teal identifies the active action. System sans type is dependable at small sizes. Borders divide working areas instead of decorative cards. No illustration or animation competes with messages.
