# Download and Run PRISM

This guide installs the completed Phase 2 project on a local computer. PRISM runs
as a Flask development application and includes the synthetic dataset and reviewed
model artifacts needed for the dashboard. Docker and Neo4j are optional.

## 1. Prerequisites

Install:

- [Python 3.11 or newer](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads) if you want to clone the repository
- A current browser such as Chrome, Edge, Firefox, or Safari

Confirm Python and Git from a terminal:

```bash
python3 --version
git --version
```

On Windows, the Python command may be `py` instead of `python3`.

## 2. Download the project

### Option A: clone with Git

```bash
git clone https://github.com/shrankhalalala/PRISM.git
cd PRISM
```

To update an existing clone later:

```bash
git pull origin main
```

### Option B: download a ZIP

1. Open the [PRISM GitHub repository](https://github.com/shrankhalalala/PRISM).
2. Select **Code → Download ZIP**.
3. Extract the ZIP archive.
4. Open a terminal in the extracted `PRISM` directory.

All commands below must be run from the repository root—the directory containing
`pyproject.toml`, `README.md`, and the `prism` folder.

## 3. Create an isolated Python environment

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-tested.txt
python -m pip install -e .
```

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-tested.txt
python -m pip install -e .
```

If PowerShell prevents activation, use Command Prompt:

```bat
.venv\Scripts\activate.bat
```

The prompt normally shows `(.venv)` after activation. Reactivate this environment
whenever you open a new terminal for the project.

## 4. Start the application

```bash
python -m prism
```

Open [http://127.0.0.1:5050](http://127.0.0.1:5050) in a browser. Keep the terminal
running while using the dashboard. Stop the server with **Ctrl+C**.

Always open PRISM through the Flask address above. Opening
`prism/templates/index.html` directly with a `file://` address bypasses Flask, so
styles, scripts, and API data will not load correctly.

## 5. Use another port

If port 5050 is already in use, choose another port before starting PRISM.

macOS or Linux:

```bash
export PRISM_PORT=5051
python -m prism
```

Windows PowerShell:

```powershell
$env:PRISM_PORT="5051"
python -m prism
```

Then open [http://127.0.0.1:5051](http://127.0.0.1:5051). To identify a process
already using port 5050, use `lsof -i :5050` on macOS/Linux or
`netstat -ano | findstr :5050` on Windows.

## 6. Verify the installation

With the virtual environment active, run:

```bash
python -m unittest discover -s tests -v
```

The completed Phase 2 repository contains 42 automated tests. You can also start
the server and check these URLs:

- [Health](http://127.0.0.1:5050/api/health)
- [Module status](http://127.0.0.1:5050/api/status)
- [OpenAPI contract](http://127.0.0.1:5050/api/openapi.json)

## 7. Regenerate data and experiments

The repository already includes the fixtures, reports, and reviewed models required
to run the application. Regeneration is optional:

```bash
python -m scripts.generate_sample
python -m scripts.prepare_data
python -m scripts.evaluate_forecasting
python -m scripts.evaluate_q_learning --episodes 500
```

The last two commands retrain models and can take longer than normal startup. They
overwrite the local Phase 2 reports and model artifacts with deterministic results.

## 8. Optional Neo4j with Docker

The dashboard does not require Neo4j. To test the graph persistence adapter, first
install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and start
Docker. Then run the following from the repository root.

macOS or Linux:

```bash
python -m pip install -e '.[neo4j]'
export NEO4J_PASSWORD='choose-a-local-password'
docker compose up -d neo4j
python -m scripts.seed_neo4j
```

Windows PowerShell:

```powershell
python -m pip install -e ".[neo4j]"
$env:NEO4J_PASSWORD="choose-a-local-password"
docker compose up -d neo4j
python -m scripts.seed_neo4j
```

Neo4j Browser is available at [http://127.0.0.1:7474](http://127.0.0.1:7474).
Stop it with `docker compose down`. Add `-v` only when you intentionally want to
delete the local Neo4j volume and its data.

## 9. Common problems

| Problem | Resolution |
|---|---|
| `python` or `python3` is not found | Install Python 3.11+ and reopen the terminal; on Windows try `py` |
| `No module named prism` | Activate `.venv`, return to the repository root, and run `python -m pip install -e .` |
| Port 5050 is already in use | Set `PRISM_PORT=5051` using the command for your operating system |
| The page has no styling or data | Use `http://127.0.0.1:5050`; do not open the HTML template directly |
| A model or fixture is missing | Run the four regeneration commands in section 7 |
| Neo4j authentication fails | Export `NEO4J_PASSWORD`, restart `docker compose`, and seed again |

The bundled data, forecasts, policies, and scenarios are synthetic research
artifacts. The application provides non-executable recommendations and is not an
operational grid-control system.
