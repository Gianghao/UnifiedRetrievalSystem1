# Contributing

## Before changing code

Read the [project vision](docs/project-vision.md), [roadmap](docs/plan.md), and [development guide](docs/development-guide.md). Check the existing implementation before assuming a feature is complete. Keep prototype limitations clear in code and documentation: the server can read messages and attachments, and the app does not provide end-to-end encryption.

## Collaboration workflow

1. Start from the current `main` branch (or the active integration branch when the team names one) and pull its latest changes.
2. Create a focused branch using `codex/<short-topic>`, such as `codex/attachment-gallery`.
3. Keep each change small enough to review and describe its user-visible behavior, data impact, and configuration or migration needs.
4. Run `npm ci` when dependencies change or the checkout is new. Start PostgreSQL and Redis with `docker compose up -d db redis` when the change needs them.
5. Run `npm run build` and the relevant tests before proposing the change. Use only a disposable database for integration tests.
6. Review `git diff` and `git status`; stage only intended repository files. Never stage the parent workspace directory or local data.
7. Use a concise commit message that names the behavior changed. Push the topic branch and open a pull request for review; do not push feature work directly to `main` unless the repository owner explicitly chooses a direct-push workflow.
8. Respond to review feedback with focused follow-up commits and update docs alongside behavior changes.

For layer boundaries and planned work, see the [development guide](docs/development-guide.md) and [roadmap](docs/plan.md).

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
- Keep architecture or data-flow docs current when introducing or moving a service boundary.
- For retrieval changes, identify the corpus, model/configuration version, source-citation behavior, and evaluation metrics used.
