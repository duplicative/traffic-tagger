# Traffic Tagger

A toolkit for security analysts, DevOps engineers, and developers to analyze captured HTTP traffic through rule-based tagging, MongoDB storage, and a web interface.

## Overview

Traffic Tagger processes CSV files containing HTTP traffic data, decodes Base64-encoded requests and responses, applies customizable YAML-based rules to tag interesting patterns, and stores the data in MongoDB. A simple web UI allows browsing and filtering tagged records.

## Prerequisites

- Docker and Docker Compose
- Sample CSV data file (see Examples)
- YAML rules file

## Installation and Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd traffic_tagger
   ```

2. Copy the environment file:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to set your MongoDB credentials if needed (defaults are provided).

3. Start the services:
   ```bash
   docker-compose up -d
   ```
   This launches MongoDB, the FastAPI backend, and Nginx frontend.

4. Verify: Open http://localhost in your browser. The web UI should load (initially empty).

## Usage

### Ingesting Data

Use the CLI to ingest CSV traffic data:

```bash
docker-compose run --rm cli ingest --file /data/traffic.csv --rules /data/rules.yaml --mongo-uri mongodb://root:password123@database:27017/http_tagger?authSource=admin
```

- `--file`: Path to CSV file (mounted via volume)
- `--rules`: Path to YAML rules file
- `--mongo-uri`: MongoDB connection string (from .env)

The CLI processes records, decodes data, applies rules, and inserts/updates MongoDB.

### Using the Web UI

- **Left Column**: Lists all unique tags with record counts. Click to select/deselect (multiple selection supported with AND logic).
- **Right Column**: Shows filtered records. Click a record to expand and view full decoded request/response.

### API Endpoints

- `GET /api/tags`: List tags with counts
- `GET /api/records?tags=tag1,tag2`: Filter records by tags (AND)
- `GET /api/record/{id}`: Get full record details

## Examples

### Sample CSV Data

Create `data/traffic.csv` (columns include `id`, `host`, `raw` (Base64 request), `response_raw` (Base64 response), etc.):

```csv
id,host,raw,response_raw,method,path,...
1,example.com,GET / HTTP/1.1...,HTTP/1.1 200 OK...,GET,/,...
```

### Sample Rules YAML

Create `data/rules.yaml`:

```yaml
rules:
  - name: "GraphQL Mutation"
    enabled: true
    conditions:
      - target: "request.path"
        operator: "contains"
        value: "graphql"
      - target: "request.body"
        operator: "contains"
        value: "mutation"
    match_logic: "AND"

  - name: "Potential PII Leak"
    enabled: true
    conditions:
      - target: "response.body"
        operator: "matches_regex"
        value: '(?i)("?email"?\s*:\s*".+@.+\..+")'
    match_logic: "AND"
```

### Ingesting and Analyzing

1. Place CSV and YAML in `data/`.
2. Run ingest command.
3. Visit web UI, select tags to filter records.

## Extending the Program

### Adding New Rules

Edit `rules.yaml` and add new rules as above. Restart ingest to apply.

### Modifying Operators

In `tagger_cli/rule_engine.py`, add to `evaluate_condition`:

```python
elif operator == 'new_operator':
    # Implement logic
```

### Custom Parsers

For new data formats, extend `tagger_cli/http_parser.py` or add modules.

### Adding API Endpoints

In `app/main.py`, add FastAPI routes.

## Dev Roadmap

- User authentication for web UI
- Real-time traffic ingestion
- Advanced visualizations and dashboards
- Support for non-CSV data formats
- Export functionality for reports
- Rule editing UI
- Performance optimizations for large datasets

## Troubleshooting

- Ensure .env is copied and variables set.
- Check Docker logs: `docker-compose logs`
- MongoDB connection issues: Verify URI in .env.

## Contributing

Fork, create branch, submit PR.

## License

MIT
