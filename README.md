# Commonplace: local development

This repository is an **incomplete local-development increment**, not a production-ready messaging or AI retrieval system. It currently contains a Next.js web app, a NestJS API, PostgreSQL schema/migration, Redis-backed rate limiting, and Docker Compose setup. Multimodal ingestion and AI retrieval are not implemented yet. Use disposable test accounts and data only; the development API prints OTP codes and phone numbers to its logs. The server can read message contents; end-to-end encryption is not implemented.

## Run it from VS Code on Windows

### Requirements

- VS Code and Git for Windows
- Docker Desktop with its Linux/WSL 2 engine running and the Compose plugin available
- Ports `3000`, `3001`, `55433`, and `6379` available on localhost

The quickest setup uses Docker for the web app, API, PostgreSQL, and Redis, so Node.js does not need to be installed on Windows for this route.

**Disk space:** Docker Desktop's virtual disk was last seen on `C:`. Docker image downloads and builds can consume additional space there. If C: is still low, move Docker Desktop's disk image to `D:\DockerData` in Docker Desktop settings before the first build. The application's PostgreSQL and Redis bind-mounted data is stored separately under this repository's `DockerData\` folder.

1. In VS Code, choose **File → Open Folder…** and open `D:\ChatGPT\Hao\unified-messaging`.
2. Start Docker Desktop and wait until it reports that the engine is running.
3. In VS Code, choose **Terminal → New Terminal**. Confirm the terminal is in the project root:

   ```powershell
   Get-Location
   ```

   The path should end in `unified-messaging`.

4. Build and start the app and its local dependencies:

   ```powershell
   docker compose up --build
   ```

   Leave this terminal running. On the first start Docker downloads the required images and builds the two app containers.

5. Open [http://localhost:3000](http://localhost:3000). To find the development verification code, open another VS Code terminal in the project root and run:

   ```powershell
   docker compose logs -f api
   ```

   Use disposable phone numbers in international format (for example, `+12025550123`). Register and sign in each test user separately. Both people must add each other's numbers before the conversation appears. Press `Ctrl+C` to stop following logs; this does not stop the app.

To stop the app, return to the terminal running Compose and press `Ctrl+C`, then run:

```powershell
docker compose down
```

This keeps the PostgreSQL and Redis development data in `DockerData\`. Do not delete that folder if you need to keep it. The local PostgreSQL port is `55433` to avoid colliding with a Windows PostgreSQL service on `5432`.

### Start the API and web app directly from VS Code (optional)

This route is useful for editing and hot reload, but you must first run PostgreSQL and Redis separately (Docker is convenient for those two services). Starting the Compose database for the first time automatically applies `db/migrations/001_foundation.sql` to its empty data directory; existing databases are not migrated automatically.

```powershell
docker compose up -d db redis
npm ci
$env:DATABASE_URL = 'postgres://app:local_password@localhost:55433/messaging'
$env:REDIS_URL = 'redis://localhost:6379'
$env:OTP_SECRET = 'local-development-secret-change-before-sharing'
$env:WEB_ORIGIN = 'http://localhost:3000'
```

The secret above is for local development only.

Then open two VS Code terminals, both at the project root. Run the API in one:

```powershell
npm run dev:api
```

Run the web app in the other:

```powershell
npm run dev:web
```

Visit [http://localhost:3000](http://localhost:3000). The API compiles once when started; restart it after API code changes. Stop host processes with `Ctrl+C`. For the Docker version, OTP output is available with `docker compose logs -f api`.

## Available checks

From the project root in a VS Code terminal:

```powershell
npm run build
npm test
npm audit --omit=dev
```

The PostgreSQL-backed OTP concurrency test is skipped unless `TEST_DATABASE_URL` points to a **dedicated disposable test database**. It creates and drops an isolated schema. Do not point it at a database containing valuable data. The current checks do not verify the whole authentication, WebSocket, or browser flow end to end.

## Push the project to GitHub

Target repository: [Gianghao/UnifiedRetrievalSystem1](https://github.com/Gianghao/UnifiedRetrievalSystem1).

First sign in to the `Gianghao` GitHub account in VS Code (Accounts icon) and make sure that account has write access to the repository. In VS Code, open **Terminal → New Terminal** at `D:\ChatGPT\Hao\unified-messaging`, then check the branch and pending files:

```powershell
git status
git branch --show-current
```

The foundation code is already committed locally on `codex/messaging-foundation`. To send that branch to GitHub, run:

```powershell
git remote add origin https://github.com/Gianghao/UnifiedRetrievalSystem1.git
git push -u origin codex/messaging-foundation
```

If Git reports that `origin` already exists, update it and retry:

```powershell
git remote set-url origin https://github.com/Gianghao/UnifiedRetrievalSystem1.git
git push -u origin codex/messaging-foundation
```

VS Code or Git Credential Manager should open a browser to authenticate. Approve GitHub access as `Gianghao`. Never paste a password or personal access token into the source files or commit one. After the push, open the repository on GitHub, choose **Compare & pull request** for `codex/messaging-foundation`, review the changes, and create the pull request. This keeps the current GitHub `main` branch intact until the changes are reviewed. If the remote branch already contains commits, fetch and inspect them before pushing; do not force-push.

For later changes, stage and commit only project files, then push the branch:

```powershell
git add README.md
git commit -m "Document local setup and GitHub workflow"
git push
```

If you edit other project files, stage their explicit paths too. Do not use `git add ..` or stage the parent `Hao` directory: it contains files unrelated to this repository and may contain private data. `.env` files, dependency directories, Docker data, local test database files, logs, and VHDX files are ignored by this repository; verify `git status` before each commit.

## Not implemented yet

The project does not yet provide a production SMS provider, full session management, contact blocking/reporting, message edits/deletion/replies, media uploads or retention cleanup, PDF/audio/video processing, embeddings, reranking, retrieval/search, grounded answers, citations, summaries, or model evaluation. No 30-day data deletion guarantee exists. See [the implementation plan](docs/plan.md) for the intended phases.
