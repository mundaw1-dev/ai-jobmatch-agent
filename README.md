
# AI JobMatch Agent

A Python-based job matching application for comparing candidate profiles with job adverts, explaining matching scores, managing a shortlist, and optionally using a locally hosted Ollama large language model (LLM) to assess individual job matches.

The application is designed for Windows development and Docker-based deployment.

## Features

- Candidate profile management.
- Job advert search and storage.
- Deterministic job matching with explainable scoring evidence.
- Matched and missing skill summaries.
- Job shortlist management.
- SQLite persistence.
- Optional local LLM assessment through Ollama.
- Docker Compose deployment.
- Configurable API credentials and runtime settings.
- Automated tests using pytest.

## Technology stack

| Component | Technology |
|---|---|
| Language | Python 3.10 |
| User interface | Streamlit |
| LLM runtime | Ollama |
| Default model | `qwen3:8b` |
| Database | SQLite |
| Container runtime | Docker |
| Multi-container orchestration | Docker Compose |
| Testing | pytest |
| Configuration | Environment variables and `.env` |

## Architecture

```text
Browser
   |
   | http://localhost:8501
   v
JobMatch Agent
(Streamlit + Python)
   |
   +---- Deterministic matching workflow
   |
   +---- SQLite database
   |       |
   |       +---- Candidate profile
   |       +---- Stored jobs
   |       +---- Shortlist
   |
   +---- Ollama HTTP API
             |
             v
          Ollama
             |
             +---- qwen3:8b
```

Docker Compose runs the application and Ollama as separate services.

Within the Docker network, the application connects to Ollama at:

`http://ollama:11434`

The application is published on the Windows host at:

`http://localhost:8501`

## Prerequisites

- Windows 10.
- Docker Desktop installed and running.
- Docker Compose v2 or later.
- Internet access to download container images and the selected model.
- Sufficient memory and disk space for the model and containers.

The default `qwen3:8b` model can require substantial memory. Model performance depends on available RAM, CPU, and compatible GPU support.

The initial Compose configuration does not explicitly enable NVIDIA GPU passthrough.

## Project location

The examples below use:

`C:\Technative\ai-jobmatch-agent`

Open Command Prompt and change to the project directory:

```bat
cd /d C:\Technative\ai-jobmatch-agent
```

## Project files

The Docker configuration adds the following files:

```text
ai-jobmatch-agent/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── README.md
├── app.py
├── config.py
├── data/
│   └── jobmatch.db
├── graph/
├── models/
├── persistence/
├── services/
├── tests/
└── ui/
```

The exact source tree depends on the files present in your local checkout.

### Dockerfile

Defines the Python application image, installs the project and starts Streamlit.

### docker-compose.yml

Defines the application and Ollama services, their networking, environment variables, ports and persistent storage.

### .dockerignore

Excludes local virtual environments, Git metadata, environment files, caches and unnecessary files from the Docker build context.

### config.py

Defines database, upload, Adzuna and Ollama configuration.

## Configuration

The Docker Compose configuration supplies these defaults:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_PATH` | `/app/data/jobmatch.db` | SQLite database location inside the container |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama service URL |
| `OLLAMA_MODEL` | `qwen3:8b` | Model used for assessments |
| `OLLAMA_TIMEOUT_SECONDS` | `300` | LLM request timeout |
| `ADZUNA_APP_ID` | Empty | Optional Adzuna application ID |
| `ADZUNA_APP_KEY` | Empty | Optional Adzuna API key |
| `ADZUNA_COUNTRY` | `gb` | Adzuna country code |

For local development, settings can be supplied through the existing `.env` file.

Do not commit `.env` or API credentials to source control.

## Build and start

### 1. Validate the configuration

```bat
docker compose config
```

Resolve any configuration errors before continuing.

### 2. Build the application image

```bat
docker compose build
```

### 3. Start the services

```bat
docker compose up -d
```

### 4. Check the service status

```bat
docker compose ps
```

### 5. Download the default Ollama model

```bat
docker compose exec ollama ollama pull qwen3:8b
```

The initial download may take time depending on the network connection.

### 6. Confirm the model is installed

```bat
docker compose exec ollama ollama list
```

### 7. Test Ollama independently

```bat
docker compose exec ollama ollama run qwen3:8b "Reply with just OK"
```

### 8. Open the application

Navigate to:

http://localhost:8501

Complete these checks in order. A running container does not necessarily mean that the model has been downloaded or that the LLM assessment workflow is working.

## Testing

Run the existing automated test suite on Windows:

```bat
.venv\Scripts\python.exe -m pytest -q
```

To run tests inside the application container, if pytest is installed in that image:

```bat
docker compose exec jobmatch-agent python -m pytest -q
```

If the production image does not contain pytest, use the Windows virtual environment for the full test suite or maintain a separate test image.

Test the following behaviours:

- Profile creation and persistence.
- Job storage and retrieval.
- Deterministic matching scores.
- Matching evidence and skill summaries.
- Shortlisting and duplicate-shortlist handling.
- Ollama connection failures and timeouts.
- Validation of structured LLM assessment responses.
- Persistence after container restart.

## Troubleshooting

### Docker configuration fails

Run:

```bat
docker compose config
```

Check the complete error output and verify that `docker-compose.yml` is saved in the project root.

### Application fails to build

Run:

```bat
docker compose build
```

Review the first relevant error in the build output. Confirm that `pyproject.toml` declares the application's runtime dependencies.

### Application is not accessible

Inspect the logs:

```bat
docker compose logs --tail=100 jobmatch-agent
```

Check that the application container is running:

```bat
docker compose ps
```

Confirm that port `8501` is not already occupied by another application.

### Ollama cannot be reached

Inspect Ollama's logs:

```bat
docker compose logs --tail=100 ollama
```

Test the Ollama API from inside its container:

```bat
docker compose exec ollama ollama list
```

When running inside Docker, the application must use `http://ollama:11434`. The address `http://localhost:11434` would refer to the application container itself, not the Ollama container.

### Ollama times out

Check that the model is installed:

```bat
docker compose exec ollama ollama list
```

Test a short prompt directly:

```bat
docker compose exec ollama ollama run qwen3:8b "Reply with just OK"
```

If this also takes too long, investigate model loading, available memory, CPU utilisation and GPU support before changing application code.

The configured timeout is an upper limit for a request, not a guarantee that the model will finish within that time.

### Inspect logs

Application:

```bat
docker compose logs -f jobmatch-agent
```

Ollama:

```bat
docker compose logs -f ollama
```

Press `Ctrl+C` to stop following the logs.

## Stop and restart

Stop the services:

```bat
docker compose down
```

Start them again:

```bat
docker compose up -d
```

Stopping the services this way does not remove the named Ollama model volume or the host-mounted application database.

Do not run `docker compose down -v` unless you intend to remove named volumes, including the downloaded Ollama models.

## Data persistence

The Compose configuration stores application data in:

`C:\Technative\ai-jobmatch-agent\data`

The Ollama model files are stored in the named Docker volume:

`ollama_models`

These are separate storage locations.

Back up the SQLite database before making schema changes or replacing application files. Protect candidate CVs, profile information and job-search data as personal information.

## Security considerations

- Do not commit API keys or `.env` files.
- The Streamlit port is bound to `127.0.0.1`, making the UI available locally rather than exposing it on every host network interface.
- The initial Compose configuration does not publish the Ollama API port to the Windows host.
- Profile and job information submitted for an LLM assessment is sent to the configured Ollama service.
- Local model execution does not, by itself, guarantee that all application activity is offline. External job-search APIs and other integrations may use the network.
- Review uploaded documents, logs and stored database records for sensitive information.

## Matching and LLM assessment

The deterministic matching workflow produces the application's match score and supporting evidence.

The LLM assessment is an additional interpretation layer intended to explain strengths, gaps, uncertainties and potential interview questions.

An LLM-generated assessment is not a verified fact and should not silently replace the deterministic score. Review the original advert and supporting evidence before relying on the assessment.

## Current implementation status

The Docker files in this guide describe the intended deployment configuration. Successful deployment has not been established merely by creating these files.

Verify the following before treating the deployment as operational:

- [ ] `docker compose config` succeeds.
- [ ] The application image builds successfully.
- [ ] Both containers start.
- [ ] Ollama downloads and runs the selected model.
- [ ] Streamlit opens at `http://localhost:8501`.
- [ ] Database data survives a container restart.
- [ ] Automated tests pass.
- [ ] The LLM assessment feature works through the application UI.

## License

Add the project's chosen licence and any third-party licence notices before distributing the application.
