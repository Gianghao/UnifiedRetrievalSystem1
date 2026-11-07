# Contributing

## Before changing code

Read the [project vision](docs/project-vision.md), [implementation plan](docs/plan.md), and this guide. Keep the current prototype's limits clear in code and documentation. The application can read message and attachment content; it does not provide end-to-end encryption.

## Development workflow

1. Start PostgreSQL and Redis with `docker compose up -d db redis`.
2. Install dependencies with `npm ci`.
3. Create a focused branch from the current project branch, for example `codex/attachment-gallery`.
4. Make the smallest complete change that preserves conversation membership checks and existing data.
5. Run `npm run build` and the relevant tests. Use a disposable database for integration tests.
6. Review `git diff` and `git status`; stage only intended project files. Do not add the parent workspace directory.
7. Commit with a short description of the behavior changed. Push a feature branch and open a pull request for review.

## Data and security rules

- Treat messages, URLs, uploads, filenames, and extracted text as untrusted input.
- Authorize conversation membership on every message, media, link, and retrieval endpoint. A supplied conversation ID never grants access.
- Validate file bytes and size on the server. Do not serve uploads from a public static directory.
- Keep test fixtures synthetic. Never use real private chats or customer attachments for retrieval experiments without informed consent.
- Do not put secrets, logs containing OTP codes, uploaded files, model weights, database files, or Docker data in Git.
- Expiration needs to cover database rows, derived text and embeddings, caches, backups, and logs before it can be presented as full deletion.
- Avoid external AI providers for private conversation content unless the user has explicitly enabled the provider and understands where the data goes.

## Pull request checklist

- Describe the user-visible behavior and any migration or configuration steps.
- Include meaningful tests for authorization, persistence, retry behavior, and failure paths when relevant.
- Update the README and technical docs when setup or system behavior changes.
- Call out unimplemented behavior and remaining privacy or retention limits.
