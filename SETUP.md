# Simple setup guide

## 1. Check the computer

Use Docker Desktop on Windows/macOS, or Docker Engine with the Compose plugin on Linux. You do not need to install Python, Node.js, PostgreSQL, or Temporal separately when using Docker.

On Windows, use Docker's WSL 2 backend and Linux containers. Virtualization must be enabled. Docker lists 8 GB system RAM in its [Windows requirements](https://docs.docker.com/desktop/setup/install/windows-install/). For a comfortable build, 16 GB RAM and several GB of free disk space are practical recommendations. Close memory-heavy applications if needed. Hardware compatibility still depends on the installed OS, available memory, and Docker support.

No GPU is required. Scripted mode runs locally; live mode calls a hosted model using your token. Internet access is needed for the first image/package downloads, and for live model requests.

Check Docker is running:

```sh
docker --version
docker compose version
docker info
```

## 2. Open a terminal in the project folder

Open the folder containing `compose.yaml`. All commands below are relative to that folder, so the project can be moved or renamed.

## 3. Start all five services

```sh
docker compose up --build -d
```

The first build downloads dependencies and can take several minutes. Later starts reuse the images. If the machine is short of memory, build serially first:

```sh
docker compose --parallel 1 build
docker compose up -d
```

Alternatively, use `docker compose build api`, then `docker compose build worker`, then `docker compose build web`.

Check status:

```sh
docker compose ps
```

The API should become healthy. A worker is also required for decisions to run; an API health check alone does not prove worker availability.

## 4. Open the screens

| Address | Purpose |
| --- | --- |
| [localhost:3000/orders](http://localhost:3000/orders) | Orders workspace; the root address redirects here |
| [localhost:3000/assistants](http://localhost:3000/assistants) | Saved assistants and New assistant |
| [localhost:3000/integrations](http://localhost:3000/integrations) | Coming-soon platform cards |
| [localhost:8000/docs](http://localhost:8000/docs) | Interactive API documentation |
| [localhost:8000/health](http://localhost:8000/health) | Database and Temporal connectivity |
| [localhost:8233](http://localhost:8233) | Temporal workflow history |

Use `localhost` consistently. These addresses refer to the computer running Docker.

Open **Assistants → New assistant**, choose **Scripted demo**, and click Create assistant. Then open **Orders → New supervision**, choose your assistant and sample, leave **Create a fresh sample ID** checked, and click **Start supervision**. A dedicated order-detail page opens; the first decision should appear within a few seconds. Follow [DEMO.md](DEMO.md).

Use **Simulate event** on that page to open the update dialog. **Add instruction** opens a separate instruction dialog. Activity, Memory, Actions, and Final report are tabs within the order page.

No setup is needed for the Integrations cards. Their logos are bundled locally and their buttons only display Coming soon.

## 5. Use the LLM token

Create a file named `.env` beside `compose.yaml`. Copy the settings from `.env.example` and enter your token:

```dotenv
LLM_API_KEY=your-provider-token
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
```

For another provider, set its Chat Completions-compatible base URL and model. The endpoint must accept `/chat/completions` with `response_format: {"type":"json_object"}`. Provider compatibility should be checked separately; token availability alone does not establish it. See the [API reference](https://developers.openai.com/api/reference/resources/chat).

Never add the token to frontend code, screenshots, or Git. `.env` is ignored. The browser cannot read it.

After editing `.env`, recreate API and worker so they receive the new values:

```sh
docker compose up -d --force-recreate api worker
```

Create a **new assistant in Live AI mode** and start a **fresh sample** through New supervision. Existing runs keep their original mode/settings. The latest-decision card labels the mode on the order-detail page. An invalid token or unavailable model produces a visible review/failure decision after bounded retries; it does not silently switch to scripted mode.

Free-text instructions are passed to the model. For the dependable contact restriction example, also tick **Customer contact requires human review**.

## 6. Stop and resume later

```sh
docker compose down
```

Database records and Temporal history remain in named volumes. Start again with `docker compose up -d`. A restarted worker resumes an existing workflow from its history.

Do not add `--volumes` unless you intend to permanently erase the local demo data. To avoid resetting anything, use **New supervision** with **Create a fresh sample ID** checked.

## Troubleshooting

| Problem | What to do |
| --- | --- |
| Cannot connect to Docker | Open Docker Desktop and wait until the engine is running |
| Port already in use | Stop the other program using 3000, 8000, or 8233 |
| No assistant decisions | Run `docker compose logs --tail=60 worker api` and inspect Temporal history |
| Dashboard connection error | Check `docker compose ps`, open `/health`, then press Retry |
| Token added but Live setup rejected | Recreate both API and worker after editing `.env` |
| Order already finished | Use New supervision with a fresh sample ID; completed order IDs are not reused |
| Pause appears delayed | Requests are asynchronous; wait for the displayed paused state |
| Build runs out of memory | Close other apps; use sequential builds; increase Docker memory if the host supports it |

## Run checks

With the services running:

```sh
docker compose exec api python -m pytest tests -q
docker compose exec api python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
```

For the end-to-end smoke test, run `python scripts/smoke.py` on Windows or `python3 scripts/smoke.py` on macOS/Linux. This script only needs standard Python. It creates uniquely named test orders and leaves their records available for inspection.
