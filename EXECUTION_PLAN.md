## **Product Requirements Document: HTTP Traffic Analysis and Tagging Engine (Project "Traffic Tagger")**

### **1. Overview**

Project "Traffic Tagger" is a toolkit designed for security analysts, DevOps engineers, and developers to analyze captured HTTP traffic. The core of the project is a powerful, rule-based tagging engine that processes HTTP requests and responses from a CSV file. These records are then stored in a MongoDB database and made searchable via a simple, clean web interface. The primary goal is to enable users to quickly sift through large amounts of traffic data to find "interesting" or "noteworthy" interactions based on a flexible, user-defined set of rules.

### **2. Goals & Objectives**

*   **Automate Analysis:** To automate the process of identifying key patterns in HTTP traffic, saving significant manual review time.
*   **Enable Customization:** To provide a highly flexible and user-configurable rule engine using a simple YAML format, allowing users to define what is "interesting" to them.
*   **Provide Fast Triage:** To offer a simple and efficient web interface for searching, filtering, and reviewing tagged traffic records.
*   **Create a Centralized Repository:** To store processed traffic data in a structured, queryable format within a MongoDB database.

### **3. Scope**

#### **3.1. In-Scope (V1)**

*   A CLI utility for ingesting and processing a CSV file of HTTP traffic.
*   Base64 decoding of raw request and response data.
*   A tagging engine that applies rules from a user-provided YAML file.
*   Storage of original and processed data (including tags) into a MongoDB collection.
*   A web application with a backend API and a simple frontend.
*   Web UI functionality to list all unique tags and filter records by one or more selected tags.
*   Web UI functionality to display the full, decoded request and response for a selected record.

#### **3.2. Out-of-Scope (V1)**

*   Real-time traffic interception or analysis.
*   User authentication or multi-user support for the web application.
*   A UI for creating or editing tagging rules (rules are edited directly in the YAML file).
*   Advanced data visualization, dashboards, or reporting.
*   Editing or deleting records from the web UI.
*   Support for data formats other than the specified CSV.

### **4. User Personas**

*   **Alex, the Security Analyst:** Alex needs to review traffic logs from a web application to hunt for potential vulnerabilities like SQL injection, cross-site scripting (XSS), or information disclosure. They will use Traffic Tagger to create rules that flag suspicious patterns and quickly filter down to only the most relevant requests.
*   **Dana, the DevOps Engineer:** Dana is responsible for application stability and performance. When debugging an issue, they need to analyze traffic dumps to understand API call sequences, check for malformed requests, or identify unexpected response codes. Traffic Tagger will help them quickly find GraphQL errors, specific API endpoints, or traffic from misbehaving clients.

### **5. Functional Requirements**

The project is composed of three primary components: the **CLI Ingestion Tool**, the **Tagging Rule Engine**, and the **Web Application**.

#### **5.1. Component 1: CLI Ingestion Tool (`tagger-cli`)**

This tool is the entry point for data processing.

*   **Command Structure:** The CLI shall be invokable as follows:
    ```bash
    tagger-cli ingest --file <path_to_csv.csv> --rules <path_to_rules.yaml> --mongo-uri <mongodb_connection_string>
    ```
*   **CSV Parsing:**
    *   The tool must parse the CSV file provided in `ref 1.1`. It should correctly map all columns as specified in the header row.
    *   It must gracefully handle potential CSV formatting errors and report them to the user.
*   **Base64 Decoding:**
    *   For each row, the `raw` (request) and `response_raw` columns must be Base64 decoded into UTF-8 strings.
    *   If decoding fails for a particular field, it should be logged, and the field in the final document should be marked as `decoding_error: true`.
*   **Rule Engine Application:**
    *   The decoded request and response text will be passed to the Tagging Rule Engine (see 5.2) for analysis.
    *   The resulting list of tags will be stored.
*   **Data Storage:**
    *   The tool will connect to the MongoDB instance specified by the `--mongo-uri`.
    *   For each row in the CSV, a single document will be inserted into a collection named `records` within a database named `http_tagger`.
    *   **Data Duplication Handling:** Before inserting, the CLI should check if a document with the same `id` from the CSV already exists. If it does, the existing document should be updated (replaced) with the new data. This makes the ingestion process idempotent.
*   **Output & Feedback:** The CLI should provide feedback during processing, such as a progress bar and a final summary:
    ```
    Processing 1500 records from traffic.csv...
    [████████████████████████████████████████] 100%
    
    Ingestion Complete.
    - Records Processed: 1500
    - Records Inserted: 1450
    - Records Updated: 50
    - Records with Tags: 327
    ```

#### **5.2. Component 2: Tagging Rule Engine**

This is the core logic that inspects data and applies tags.

*   **YAML Rule Definition:** The engine will parse a YAML file with a list of rules. The structure must be as follows:

    ```yaml
    rules:
      - name: "Interesting Content-Type"
        enabled: true
        conditions:
          - target: "response.headers.content-type"
            operator: "contains"
            value: "javascript"
          - target: "response.headers.content-type"
            operator: "contains"
            value: "html"
        match_logic: "OR" # This rule matches if ANY condition is true
    
      - name: "GraphQL Mutation"
        enabled: true
        conditions:
          - target: "request.path"
            operator: "contains"
            value: "graphql"
          - target: "request.body"
            operator: "contains"
            value: "mutation"
        match_logic: "AND" # This rule matches only if ALL conditions are true
    
      - name: "Potential PII Leak"
        enabled: true
        conditions:
          - target: "response.body"
            operator: "matches_regex"
            value: '(?i)("?email"?\s*:\s*".+@.+\..+")' # Regex to find email patterns
        match_logic: "AND"
    ```
*   **Engine Logic:**
    1.  For each HTTP record, initialize an empty list of tags.
    2.  Iterate through each `enabled: true` rule in the YAML file.
    3.  For each rule, evaluate its conditions against the record data.
    4.  The engine must be able to parse the decoded HTTP text to access:
        *   `request.method`, `request.path`, `request.http_version`
        *   `request.headers` (as a key-value map, keys should be case-insensitive)
        *   `request.body`
        *   `response.status_code`, `response.status_message`
        *   `response.headers` (as a key-value map, keys should be case-insensitive)
        *   `response.body`
    5.  **Operators:** The engine must support the following operators:
        *   `contains`: The target string contains the value string (case-insensitive).
        *   `not_contains`: The target string does not contain the value string (case-insensitive).
        *   `equals`: The target string exactly matches the value string.
        *   `starts_with`: The target string starts with the value string.
        *   `ends_with`: The target string ends with the value string.
        *   `matches_regex`: The target string matches the provided PCRE regular expression.
    6.  **Condition Matching:** The `match_logic` field determines how conditions are combined. It supports `AND` (all must be true) and `OR` (any can be true). If omitted, it defaults to `AND`.
    7.  If a rule's conditions are met, its `name` is added to the record's list of tags.

#### **5.3. Component 3: MongoDB Data Store**

*   **Database:** `http_tagger`
*   **Collection:** `records`
*   **Document Schema:** Each document in the `records` collection must have the following structure:
    ```json
    {
      "_id": "<ObjectId>",
      "source_id": 56, // from the 'id' column in the CSV
      "host": "www.compass.com",
      "method": "GET",
      "path": "/api/v3/similarhomes/recommendations",
      // ... include ALL other original columns from the CSV ...
      "response_created_at": 1729389528919,
      
      // --- Added by the Tagger Engine ---
      "decoded_request": "GET /api/v3/similarhomes/recommendations?json... HTTP/1.1\r\nHost: ...",
      "decoded_response": "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n...",
      "tags": [
        "Interesting Content-Type",
        "API Call"
      ],
      "processed_at": "<ISO 8601 Timestamp>"
    }
    ```
*   **Indexes:** To ensure efficient querying by the web application, create indexes on the following fields:
    *   `tags` (Multikey Index)
    *   `source_id` (Unique Index)
    *   `host`

#### **5.4. Component 4: Web Application (`tagger-web`)**

A simple, single-page application for data exploration.

*   **Backend API (e.g., using FastAPI or Flask):**
    *   `GET /api/tags`:
        *   **Description:** Fetches all unique tags present in the database along with the count of records for each tag.
        *   **Response Body:**
            ```json
            {
              "tags": [
                { "name": "GraphQL Mutation", "count": 15 },
                { "name": "Interesting Content-Type", "count": 152 },
                { "name": "API Call", "count": 890 }
              ]
            }
            ```
    *   `GET /api/records`:
        *   **Description:** Fetches records, with support for filtering by tags.
        *   **Query Parameters:** `tags` (a comma-separated list of tag names, e.g., `?tags=API Call,GraphQL Mutation`). When multiple tags are provided, records matching **all** specified tags should be returned (AND logic).
        *   **Response Body:** An array of record summaries (not the full decoded data to keep the payload small).
            ```json
            {
              "records": [
                {
                  "id": "<ObjectId>",
                  "source_id": 56,
                  "host": "www.compass.com",
                  "method": "GET",
                  "path": "/api/v3/similarhomes/recommendations",
                  "response_status_code": 200,
                  "tags": ["API Call"]
                }
              ]
            }
            ```
    *   `GET /api/record/{record_id}`:
        *   **Description:** Fetches the complete details for a single record by its MongoDB `_id`.
        *   **Response Body:** The full MongoDB document, including `decoded_request` and `decoded_response`.

*   **Frontend UI (HTML/CSS/Vanilla JS):**
    *   **Layout:** A two-column layout.
        *   **Left Column (Filters):**
            *   A list of all available tags fetched from `/api/tags`. Each tag should be a clickable button or checkbox.
            *   Display the count next to each tag name.
        *   **Right Column (Results):**
            *   Displays a list of records matching the selected filters.
            *   Each record summary (from `/api/records`) should be an expandable item.
            *   When a record summary is clicked, it should expand to show the full, formatted `decoded_request` and `decoded_response` fetched from `/api/record/{id}`. Use a monospace font and pre-formatted text (`<pre>`) for readability.

### **6. Non-Functional Requirements**

*   **Performance:** The CLI should be able to process at least 10,000 records per minute on a standard developer machine. The web UI API responses should complete in under 500ms for typical queries.
*   **Usability:** The CLI must provide clear instructions and error messages. The web UI must be intuitive and require no training to use.
*   **Error Handling:** The system must be resilient to malformed data (e.g., invalid Base64, missing CSV columns) and log errors clearly without crashing.
*   **Configuration:** The YAML rule format should be well-documented with examples.

### **7. Technical Stack (Recommendation)**

*   **CLI & Backend:** Python 3.10+ (using `Typer`/`Click` for CLI, `FastAPI` for the web backend, `PyYAML` for rules, and `pymongo` for DB access).
*   **Database:** MongoDB 5.0+
*   **Frontend:** HTML5, CSS3, Vanilla JavaScript (no complex framework required for V1).

### **8. Deployment Requirements**

To ensure a consistent, reproducible, and easy-to-use environment for both development and deployment, the entire application stack must be orchestrated using Docker and Docker Compose. A user should be able to get the entire system running with a minimal set of commands.

#### **8.1. Docker Compose Services**

The root of the project repository must contain a `docker-compose.yml` file that defines the following services:

1.  **`database`**:
    *   **Image:** Use the official `mongo` image from Docker Hub (e.g., `mongo:5.0`).
    *   **Data Persistence:** MongoDB data must be persisted outside the container using a named Docker volume to prevent data loss when the container is stopped or removed.
    *   **Configuration:** The root username and password must be configured via environment variables.

2.  **`api`**:
    *   **Build:** This service must be built from a custom `Dockerfile` located within the project. The Dockerfile should install Python, the required dependencies (from a `requirements.txt` file), and run the FastAPI (or equivalent) web server.
    *   **Networking:** It must be on the same Docker network as the `database` service to allow for communication using the service name (e.g., `mongodb://database:27017`).
    *   **Environment:** The MongoDB connection string should be passed in as an environment variable from a `.env` file.

3.  **`frontend`**:
    *   **Image:** Use the official `nginx` image from Docker Hub.
    *   **Configuration:** A custom `nginx.conf` must be used to:
        *   Serve the static HTML, CSS, and JavaScript files for the web application.
        *   Act as a reverse proxy for the API. Requests to `/api/*` on the frontend service should be forwarded to the `api` service (e.g., `proxy_pass http://api:8000;`). This avoids CORS issues in the browser.
    *   **Volumes:** The static content and the custom Nginx configuration must be mounted into the container using volumes.

4.  **`cli`**:
    *   **Build:** This service should be built from a dedicated `Dockerfile`, which can share the same base image and dependencies as the `api` service.
    *   **Purpose:** This service is **not** for long-running processes. It is designed to be used on-demand for data ingestion via the `docker-compose run` command.
    *   **Configuration:** The `docker-compose.yml` entry for this service should ensure it does not start automatically with `docker-compose up`. It should be configured to mount the local directory where data files (CSVs, YAML rules) are stored so they can be accessed from within the container.

#### **8.2. Configuration and Developer Workflow**

*   **Environment File:** A `.env.example` file must be included in the repository. A developer will copy this to `.env` and fill in the necessary configuration (e.g., database credentials). The `docker-compose.yml` file must be configured to read this `.env` file.
*   **Startup Command:** The primary command to launch the web application and database will be `docker-compose up -d`.
*   **Ingestion Command:** The command to run the ingestion process will be:
    ```bash
    docker-compose run --rm cli ingest --file /data/traffic.csv --rules /data/rules.yaml --mongo-uri <mongo_connection_string_from_env>
    ```
    *(Note: `/data/` is the path inside the container where local files are mounted.)*

### **9. Non-Functional Requirements**

*   **Performance:** The CLI should be able to process at least 10,000 records per minute on a standard developer machine. The web UI API responses should complete in under 500ms for typical queries.
*   **Usability:** The CLI must provide clear instructions and error messages. The web UI must be intuitive and require no training to use. The Docker Compose setup should allow a new developer to have the system running in under 5 minutes.
*   **Error Handling:** The system must be resilient to malformed data (e.g., invalid Base64, missing CSV columns) and log errors clearly without crashing.
*   **Configuration:** The YAML rule format should be well-documented with examples.

### **10. Technical Stack (Recommendation)**

*   **Orchestration:** Docker & Docker Compose
*   **CLI & Backend:** Python 3.10+ (using `Typer`/`Click` for CLI, `FastAPI` for the web backend, `PyYAML` for rules, and `pymongo` for DB access).
*   **Database:** MongoDB 5.0+
*   **Frontend Web Server:** Nginx
*   **Frontend UI:** HTML5, CSS3, Vanilla JavaScript (no complex framework required for V1).

### **11. Acceptance Criteria**

*   **Given** a CSV file and a YAML rule file with the "GraphQL Mutation" rule,
    *   **When** I run `tagger-cli ingest ...`,
    *   **Then** the process completes successfully, and records with "graphql" in the path and "mutation" in the body are tagged with "GraphQL Mutation" in MongoDB.

*   **Given** data has been ingested into MongoDB,
    *   **When** I open the web application,
    *   **Then** I see a list of all unique tags and their counts in the left column.

*   **Given** I am on the web application page,
    *   **When** I click on the "GraphQL Mutation" tag,
    *   **Then** the right column updates to show only the records that have that tag.

*   **Given** a list of filtered records is displayed,
    *   **When** I click on a specific record,
    *   **Then** it expands to show the full, formatted decoded request and response for that record.

*   **Given** a fresh clone of the project repository and Docker installed,
    *   **When** I create a `.env` file, run `docker-compose up -d`, and then execute the `docker-compose run --rm cli ingest ...` command with a sample data file,
    *   **Then** all services start without errors, the data is ingested into the MongoDB container, and the web UI is fully functional and accessible at `http://localhost:80` (or another specified port).

