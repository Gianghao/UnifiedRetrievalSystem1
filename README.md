# Commonplace

Commonplace is a local-first messaging prototype with a planned unified retrieval assistant. The assistant is intended to answer questions using evidence shared in a conversation, such as messages and attached documents or media. The current project is the messaging and shared-item foundation; **retrieval, transcription, embeddings, and answer generation are not implemented yet**.

This is a development prototype. Do not use it for sensitive conversations. The local OTP code appears in API logs, there is no end-to-end encryption, and attachment expiration is not a verified secure-erasure or backup-retention policy.

## Current status

- Phone-based registration and sign-in with a development-only OTP flow.
- Mutual contacts and one-to-one conversations.
- Persisted text messages, read receipts, pagination, and WebSocket refresh notifications.
- JPEG, PNG, GIF, WebP, MP3, WAV, Ogg, WebM, MP4, and PDF attachments up to 20 MiB each. The API checks file signatures and requires conversation membership to upload or retrieve files.
- A conversation details panel opened from the other person's name. Its **Media**, **Files**, and **Links** tabs browse shared items with pagination.
- Attachment bytes expire 30 days after sending. While the API is running, hourly cleanup clears expired bytes; the filename and message remain. Database storage space is not reclaimed automatically.

Known gaps include production SMS, full session management and account recovery, blocking/reporting, message edits/deletion/replies, malware scanning, external object storage, data backup policy, complete browser end-to-end tests, and all AI processing and retrieval capabilities. Read [the project vision](docs/project-vision.md) and [the implementation plan](docs/plan.md) before adding features that depend on retrieval or media processing.

## Run locally on Windows

### Requirements

- Visual Studio Code and Git for Windows
- Docker Desktop with its WSL 2 engine running and the Docker Compose plugin
- Ports `3000`, `3001`, `55433`, and `6379` free on localhost

Open `D:\ChatGPT\Hao\unified-messaging` in VS Code, start Docker Desktop, then use **Terminal → New Terminal**:

```powershell
docker compose up -d --build
```

Open [http://localhost:3000](http://localhost:3000). To view a development sign-in code, open another terminal and run:

```powershell
docker compose logs -f api
```

Use disposable accounts and valid international phone numbers. Registration and sign-in are separate: register, request a new code, then sign in. Both users must add each other's numbers to create a conversation. From the chat, select the other person's name to browse shared media, files, and links.

Stop the app with:

```powershell
docker compose down
```

This preserves the data directories configured in `docker-compose.yml`. Do not remove them if you need the local database or Redis data. Docker Desktop stores its virtual disk at `D:\DockerData\DockerDesktopWSL` on the original development machine; contributors can set a different Docker disk location in Docker Desktop settings.

### Upgrade an existing database

Compose runs SQL files in `db/migrations` automatically only when PostgreSQL initializes an empty data directory. If your database predates attachment support, apply the additive migration once, then rebuild:

```powershell
docker compose up -d db
Get-Content -Raw db/migrations/002_attachments.sql | docker compose exec -T db psql -v ON_ERROR_STOP=1 -U app -d messaging
docker compose up -d --build
```

### Run services from VS Code for development

Keep PostgreSQL and Redis running through Compose, then install workspace dependencies:

```powershell
docker compose up -d db redis
npm ci
$env:DATABASE_URL = 'postgres://app:local_password@localhost:55433/messaging'
$env:REDIS_URL = 'redis://localhost:6379'
$env:OTP_SECRET = 'local-development-secret-change-before-sharing'
$env:WEB_ORIGIN = 'http://localhost:3000'
```

For an existing database, apply any migration that has not already been applied. Start the API in one terminal and the web app in another:

```powershell
npm run dev:api
npm run dev:web
```

The API compiles once on startup. Restart it after API changes.

## Checks

From the repository root:

```powershell
npm run build
npm test
npm audit --omit=dev
```

The PostgreSQL concurrency test uses `TEST_DATABASE_URL` if set. The attachment integration test also requires `TEST_REDIS_URL` and a built API. Both tests create and remove isolated schemas; use a disposable local test database. Never point them at a database with valuable data.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch, change, security, and review expectations. The [development guide](docs/development-guide.md) describes the product goal, current and planned architecture, collaboration rules, and design artifacts. Never commit `.env` files, credentials, Docker data, user attachments, model files, or local databases. Before staging, inspect `git status` and stage only files inside this repository.
