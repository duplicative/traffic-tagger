# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

HTTP Traffic Tagger is a Docker-based HTTP traffic analysis toolkit with a rule-based tagging engine. It ingests Base64-encoded HTTP request/response pairs from CSV files, applies YAML-defined rules to tag traffic, stores data in MongoDB, and provides a web UI for filtering and viewing tagged records.

## Architecture

### Service Architecture (Docker Compose)
- **database**: MongoDB 5.0 for storing tagged HTTP records
- **api**: FastAPI backend exposing REST endpoints
- **frontend**: Nginx serving static HTML/CSS/JS with reverse proxy to API
- **cli**: On-demand CLI tool for manual CSV ingestion (not auto-started)
- **watcher**: Hot reload service that auto-ingests CSVs and re-tags on rule changes

### Core Modules (shared/)
- **http_parser.py**: Parses raw HTTP strings into structured dicts (method, path, headers, body, status codes)
- **rule_engine.py**: Evaluates HTTP traffic against YAML rules, returns matched tags AND matched string values (highlights)

### Data Flow
1. CSV files with Base64-encoded HTTP data → CLI or Watcher
2. Base64 decode → HTTP parsing → Rule engine tagging
3. Store in MongoDB with tags + highlights dict
4. API exposes records → Frontend displays with color-coded tag highlights

## Development Commands

### Start/Stop Services
```bash
# Start all services (database, api, frontend, watcher)
docker-compose up -d

# View logs for specific service
docker compose logs -f watcher
docker compose logs -f api

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose build --no-cache
docker-compose up -d
```

### Data Ingestion
```bash
# Automatic (recommended): Drop CSV into data/ directory
cp your_traffic.csv data/
# Watcher auto-processes within 5 seconds

# Manual CLI ingestion
docker-compose run --rm cli --file /data/traffic.csv --rules /data/rules.yaml

# Check ingestion progress
docker compose logs -f watcher
```

### MongoDB Access
```bash
# Access MongoDB shell
docker exec -it traffic_tagger_mongo mongosh -u admin -p admin

# View records
use http_tagger
db.records.find().limit(5)

# View tags
db.records.distinct("tags")
```

### Python Development (Virtual Environment)
```bash
# Always use virtual env when running Python outside Docker
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run components locally (requires MongoDB running)
cd api && uvicorn main:app --reload --port 8000
python -m cli.main --file data/traffic.csv --rules data/rules.yaml
```

## Key Implementation Details

### Rule Engine Behavior
- Returns tuple: `(tags: List[str], highlights: Dict[str, List[str]])`
- `highlights` maps rule name → list of matched string values
- Operators: `contains`, `not_contains`, `equals`, `starts_with`, `ends_with`, `matches_regex`
- Match logic: `AND` (all conditions) or `OR` (any condition)

### MongoDB Schema
- Database: `http_tagger`
- Collection: `records`
- Key fields: `source_id` (unique), `tags` (multikey index), `decoded_request`, `decoded_response`, `highlights`
- Indexes: `tags`, `source_id`, `host`

### Hot Reload (Watcher Service)
- **Rules reload**: Editing `data/rules.yaml` triggers re-tagging of ALL existing records
- **CSV auto-ingest**: New CSV files in `data/` are auto-processed and tracked in `watcher_metadata` collection
- **Debounce**: 5-second delay after last change before processing
- **Duplicate prevention**: Processed CSV filenames stored in MongoDB to prevent re-ingestion

### Frontend Highlighting
- Each tag gets a unique color from a 20-color palette (assigned at runtime)
- Matched text in HTTP content is highlighted with tag's color
- Colors consistent across: tag badges, filter pills, and HTTP content highlights

### CSV Format Requirements
- Must have columns: `id`, `host`, `method`, `path`, `response_status_code`, `raw` (Base64 request), `response_raw` (Base64 response)
- Field size limit: 10MB (handles large Base64-encoded traffic)

## Important Constraints

### Authentication/Authorization
**CRITICAL**: Do NOT implement authentication or authorization. This is explicitly prohibited per AGENTS.md. The system is designed for local development and trusted environments only.

### Progress Tracking
When completing development tasks:
1. Review EXECUTION_PLAN.md for task requirements
2. Update PROGRESS.md with completion summary and next steps
3. Append feature to LOG_BOOK.md in format: `## Feature Name | YYYY-MM-DD\nDescription.`

### Web UI Access
- Frontend: http://localhost:9999
- API: http://localhost:8000
- MongoDB: localhost:27017

## Common Issues

### CSV Field Size Errors
If ingestion fails with "field size exceeded", increase limit in `cli/main.py`:
```python
csv.field_size_limit(10 * 1024 * 1024)  # Currently 10MB
```

### Watcher Not Processing Files
- Check file permissions in `data/` directory
- Verify watcher container is running: `docker-compose ps`
- Check for previous processing: Query `watcher_metadata` collection
- Review logs: `docker compose logs -f watcher`

### Rules Not Applying
- Validate YAML syntax in `data/rules.yaml`
- Check rule enabled: `enabled: true`
- Verify target paths match HTTP structure (e.g., `request.headers.content-type`)
- Test with `python debug_rules.py` if available

### MongoDB Connection Issues
- Check `.env` file has correct `MONGO_URI`
- Ensure database container is running: `docker-compose ps database`
- Verify network connectivity: All services must be on `tagger_network`
