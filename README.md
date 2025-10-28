# HTTP Traffic Tagger

A powerful toolkit for security analysts and developers to analyze captured HTTP traffic using a flexible, rule-based tagging engine. Store, search, and explore HTTP request/response pairs through a clean web interface.

## Features

- **Rule-Based Tagging Engine**: Define custom rules in YAML to automatically tag interesting HTTP traffic
- **MongoDB Storage**: Centralized storage for all processed traffic data
- **Web Interface**: Simple, intuitive UI for filtering and exploring tagged records
- **Docker Compose**: Complete containerized stack for easy deployment
- **Base64 Decoding**: Automatic decoding of Base64-encoded HTTP data
- **Flexible Filtering**: Filter records by multiple tags using AND logic

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- At least 2GB of available RAM
- HTTP traffic data in CSV format (with Base64-encoded raw request/response)

### Installation

1. **Clone the repository:**
   ```bash
   cd /path/to/traffic_tagger
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env if needed (default values should work for local development)
   ```

3. **Start the services:**
   ```bash
   docker-compose up -d
   ```

   This will start:
   - MongoDB database (port 27017)
   - FastAPI backend (port 8000)
   - Nginx frontend (port 9999)

4. **Verify services are running:**
   ```bash
   docker-compose ps
   ```

### Ingesting Data

1. **Prepare your data:**
   - Place your CSV file in the `data/` directory
   - Create or copy a rules file (see `data/rules.example.yaml`)

2. **Run the ingestion CLI:**
   ```bash
   docker-compose run --rm cli ingest --file /data/your_traffic.csv --rules /data/rules.yaml --mongo-uri "mongodb://admin:password123@database:27017/"
   ```

3. **Monitor progress:**
   The CLI will display a progress summary:
   ```
   Processing records from /data/your_traffic.csv...
   
   Ingestion Complete.
   - Records Processed: 1500
   - Records Inserted/Updated: 1500
   - Records with Tags: 327
   ```

### Accessing the Web UI

1. Open your browser to `http://localhost:9999`
2. Tags will appear in the left sidebar with record counts
3. Click tags to filter records
4. Click a record to expand and view full request/response details

## Project Structure

```
traffic_tagger/
├── api/                    # FastAPI backend
│   ├── Dockerfile
│   ├── main.py            # API endpoints
│   └── __init__.py
├── cli/                    # CLI ingestion tool
│   ├── Dockerfile
│   ├── main.py            # CLI commands
│   └── __init__.py
├── shared/                 # Shared modules
│   ├── http_parser.py     # HTTP request/response parser
│   ├── rule_engine.py     # Tagging rule engine
│   └── __init__.py
├── frontend/               # Web UI
│   ├── nginx/
│   │   └── nginx.conf     # Nginx configuration
│   └── static/
│       ├── index.html     # Main HTML page
│       ├── styles.css     # CSS styles
│       └── app.js         # JavaScript application
├── data/                   # Data directory (mounted in CLI container)
│   └── rules.example.yaml # Example rules file
├── docker-compose.yml      # Docker Compose configuration
├── requirements.txt        # Python dependencies
├── .env.example            # Example environment variables
└── README.md              # This file
```

## CSV Format

The ingestion tool expects a CSV file with the following columns:

- `id`: Unique identifier for the record
- `host`: Host name
- `method`: HTTP method (GET, POST, etc.)
- `path`: Request path
- `http_version`: HTTP version
- `scheme`: URL scheme (http/https)
- `authority`: Authority component
- `request_content_length`: Request content length
- `request_timestamp_start`: Request start timestamp
- `request_timestamp_end`: Request end timestamp
- `response_status_code`: HTTP response status code
- `response_reason`: Response reason phrase
- `response_content_length`: Response content length
- `response_timestamp_start`: Response start timestamp
- `response_timestamp_end`: Response end timestamp
- `response_created_at`: Response creation timestamp
- `raw`: **Base64-encoded raw HTTP request**
- `response_raw`: **Base64-encoded raw HTTP response**

## Rule Engine

### Rule Structure

Rules are defined in YAML format:

```yaml
rules:
  - name: "Rule Name"
    enabled: true
    conditions:
      - target: "request.path"
        operator: "contains"
        value: "/api/"
    match_logic: "AND"
```

### Targets

Available targets for conditions:

**Request:**
- `request.method`
- `request.path`
- `request.http_version`
- `request.headers.<header-name>` (e.g., `request.headers.content-type`)
- `request.body`

**Response:**
- `response.status_code`
- `response.status_message`
- `response.headers.<header-name>` (e.g., `response.headers.content-type`)
- `response.body`

### Operators

- `contains`: Case-insensitive substring match
- `not_contains`: Case-insensitive negative substring match
- `equals`: Exact string match
- `starts_with`: String starts with value
- `ends_with`: String ends with value
- `matches_regex`: PCRE regular expression match

### Match Logic

- `AND`: All conditions must be true (default)
- `OR`: Any condition can be true

### Example Rules

```yaml
rules:
  # Tag all GraphQL mutations
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

  # Tag responses with interesting content types
  - name: "Interesting Content-Type"
    enabled: true
    conditions:
      - target: "response.headers.content-type"
        operator: "contains"
        value: "javascript"
      - target: "response.headers.content-type"
        operator: "contains"
        value: "html"
    match_logic: "OR"

  # Tag potential PII leaks
  - name: "Potential PII Leak"
    enabled: true
    conditions:
      - target: "response.body"
        operator: "matches_regex"
        value: '(?i)(email|ssn|credit|password)'
    match_logic: "AND"
```

## API Endpoints

### GET /api/tags

Returns all unique tags with their counts.

**Response:**
```json
{
  "tags": [
    {"name": "GraphQL Mutation", "count": 15},
    {"name": "API Call", "count": 890}
  ]
}
```

### GET /api/records?tags=<tags>

Returns records filtered by tags (comma-separated, AND logic).

**Parameters:**
- `tags` (optional): Comma-separated list of tag names

**Response:**
```json
{
  "records": [
    {
      "id": "507f1f77bcf86cd799439011",
      "source_id": 56,
      "host": "www.example.com",
      "method": "GET",
      "path": "/api/v1/users",
      "response_status_code": 200,
      "tags": ["API Call", "JSON Response"]
    }
  ]
}
```

### GET /api/record/{record_id}

Returns full details for a single record.

**Response:**
```json
{
  "id": "507f1f77bcf86cd799439011",
  "source_id": 56,
  "host": "www.example.com",
  "method": "GET",
  "path": "/api/v1/users",
  "decoded_request": "GET /api/v1/users HTTP/1.1\r\nHost: ...",
  "decoded_response": "HTTP/1.1 200 OK\r\nContent-Type: ...",
  "tags": ["API Call"],
  ...
}
```

## Development

### Local Development (without Docker)

1. **Install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Start MongoDB locally** or use a cloud instance

3. **Run the API:**
   ```bash
   cd api
   uvicorn main:app --reload --port 8000
   ```

4. **Run the CLI:**
   ```bash
   python -m cli.main ingest --file data/traffic.csv --rules data/rules.yaml --mongo-uri "mongodb://localhost:27017/"
   ```

## Troubleshooting

### Services won't start

```bash
# Check logs
docker-compose logs

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Cannot connect to MongoDB

- Ensure `.env` file has correct credentials
- Check if MongoDB container is running: `docker-compose ps`
- Check MongoDB logs: `docker-compose logs database`

### CLI ingestion fails

- Verify CSV file is in the `data/` directory
- Check that the file path in the command uses `/data/` (the container mount point)
- Verify the rules YAML file is valid
- Check MongoDB connection string is correct

### Web UI shows no tags

- Ensure data has been ingested successfully
- Check API logs: `docker-compose logs api`
- Verify API is accessible: `curl http://localhost:8000/api/tags`

## Performance

- The CLI can process ~10,000 records per minute on a standard machine
- API responses complete in <500ms for typical queries
- MongoDB indexes are automatically created for efficient querying

## Security Notes

- No authentication/authorization is implemented (V1)
- This is intended for local development and analysis environments
- Do not expose services to the public internet without proper security measures

## License

This project is provided as-is for educational and professional use.

## Contributing

Issues and pull requests are welcome. Please ensure code follows existing patterns and includes appropriate error handling.
