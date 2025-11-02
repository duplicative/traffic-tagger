# Gemini Context: HTTP Traffic Tagger
**Upon beginning a session always review the AGENTS.md file for operational instructions**

## 1. Project Overview

This project, "HTTP Traffic Tagger," is a full-stack application designed for security analysts and developers to analyze captured HTTP traffic. It allows users to ingest HTTP request/response data from CSV files, apply a flexible, user-defined set of rules to "tag" interesting records, and then search and explore this data through a simple web interface.

**Core Technologies:**
*   **Backend:** Python with FastAPI, serving a REST API for the frontend.
*   **Frontend:** Plain JavaScript, HTML, and CSS, served by an Nginx web server.
*   **Database:** MongoDB for storing all traffic records, tags, and metadata.
*   **Rule Engine:** A custom YAML-based engine for defining tagging logic.
*   **Orchestration:** Docker and Docker Compose are used to containerize and run all services.

**Architecture:**
The application is composed of several microservices:
*   `api`: The FastAPI backend that provides endpoints to query tags and records.
*   `frontend`: The Nginx server that hosts the static web UI files.
*   `database`: The MongoDB instance for data persistence.
*   `watcher`: A Python service using the `watchdog` library to monitor the `/data` directory for new CSV files and changes to the `rules.yaml` file, providing hot-reload capabilities.
*   `cli`: A command-line interface for manual data ingestion.

## 2. Building and Running

The primary method for running the application is through Docker Compose.

**1. Start All Services:**
```bash
# Start all services in detached mode
docker-compose up -d
```
This command will start the API (default: port 8000), Frontend (default: port 9999), Database (port 27017), and the Watcher service.

**2. Ingesting Data:**
*   **Automatic (Hot-Reload):** Copy a CSV file (with the specified format in `README.md`) into the `./data/` directory. The `watcher` service will automatically detect and process it.
*   **Manual:** Use the CLI service for one-time ingestion.
    ```bash
    docker compose run --rm cli --file /data/your_traffic.csv --rules /data/rules.yaml
    ```

**3. Modifying Rules:**
*   Edit the `data/rules.yaml` file. The `watcher` service will detect the changes, reload the rules, and automatically re-tag all existing records in the database.

**4. Local Development (without Docker):**
As per the `README.md`, a local development setup is also possible:
```bash
# 1. Set up a virtual environment
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the API (assuming a local MongoDB instance is running)
cd api
uvicorn main:app --reload --port 8000
```

## 3. Development Conventions

*   **Agent-Based Development:** The `AGENTS.md` file specifies a workflow for AI agents. Development tasks are driven by an `EXECUTION_PLAN.md`, with progress tracked in `PROGRESS.md` and a changelog maintained in `LOG_BOOK.md`. Agents should review these files before starting work.
*   **Modular Structure:** The project is divided into clear, single-responsibility services (`api`, `cli`, `watcher`). Shared business logic, such as the `RuleEngine` and `HTTPParser`, is located in the `shared/` directory.
*   **Configuration:**
    *   Environment variables (e.g., ports, MongoDB URI) are managed via a `.env` file, sourced by `docker-compose.yml`.
    *   The core tagging logic is externalized into `data/rules.yaml`, allowing for changes without code modification.
*   **Data Schema:** The API (`api/main.py`) defines Pydantic models (`RecordSummary`, `RecordDetail`) that reflect the data structure stored in MongoDB.
*   **Highlights Feature:** The rule engine (`shared/rule_engine.py`) has been updated to not only tag records but also to return the specific substrings (`highlights`) that caused a rule to match. This data is stored in the `highlights` field in MongoDB and is exposed via the `/api/record/{record_id}` endpoint.

## Active Technologies
- Python 3.11 + FastAPI (backend), plain JavaScript (frontend) (001-raw-data-browser)
- MongoDB 5.0 (001-raw-data-browser)

## Recent Changes
- 001-raw-data-browser: Added Python 3.11 + FastAPI (backend), plain JavaScript (frontend)
