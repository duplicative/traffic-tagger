# Project "Traffic Tagger"

Project "Traffic Tagger" is a toolkit designed for security analysts, DevOps engineers, and developers to analyze captured HTTP traffic. The core of the project is a powerful, rule-based tagging engine that processes HTTP requests and responses from a CSV file. These records are then stored in a MongoDB database and made searchable via a simple, clean web interface. The primary goal is to enable users to quickly sift through large amounts of traffic data to find "interesting" or "noteworthy" interactions based on a flexible, user-defined set of rules.

## Features

*   **Automated Analysis:** Automates the process of identifying key patterns in HTTP traffic.
*   **Flexible Rule Engine:** A highly flexible and user-configurable rule engine using a simple YAML format.
*   **Simple Web Interface:** A clean and efficient web interface for searching, filtering, and reviewing tagged traffic records.
*   **Centralized Storage:** Stores processed traffic data in a structured, queryable format within a MongoDB database.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Docker
*   Docker Compose

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/traffic-tagger.git
    cd traffic-tagger
    ```

2.  **Create the environment file:**
    Copy the example environment file and modify it if necessary.
    ```bash
    cp .env.example .env
    ```

3.  **Build and start the services:**
    ```bash
    docker compose up -d --build
    ```
    This will start the following services:
    *   `database`: A MongoDB instance.
    *   `api`: The backend API.
    *   `frontend`: The Nginx web server for the frontend.

## Usage

### CLI Ingestion Tool (`tagger-cli`)

The `tagger-cli` is used to ingest and process HTTP traffic from a CSV file.

**Command:**
```bash
docker compose run --rm cli ingest --file /data/traffic.csv --rules /data/rules.yaml --mongo-uri <mongo_connection_string_from_env>
```

**Arguments:**

*   `--file`: The path to the CSV file to ingest (inside the container).
*   `--rules`: The path to the YAML file with tagging rules (inside the container).
*   `--mongo-uri`: The MongoDB connection string.

### Web Application (`tagger-web`)

The web application provides a simple interface to explore the tagged traffic data.

1.  **Access the web UI:**
    Open your browser and navigate to `http://localhost:8080`.

2.  **Features:**
    *   **Tag Filtering:** The left column displays a list of all unique tags. Click on a tag to filter the records.
    *   **Record Inspection:** The right column displays the records. Click on a record to view the full decoded request and response.

## Extending Functionality

### Adding New Rules

The tagging engine is controlled by a YAML file (e.g., `rules.yaml`). You can add new rules to this file to customize the tagging process.

**Rule Structure:**

```yaml
rules:
  - name: "Rule Name"
    enabled: true
    conditions:
      - target: "target_field"
        operator: "operator"
        value: "value"
    match_logic: "AND" # or "OR"
```

*   `name`: The name of the tag to apply if the rule matches.
*   `enabled`: Set to `true` to enable the rule.
*   `conditions`: A list of conditions to evaluate.
*   `target`: The field to inspect in the HTTP record.
*   `operator`: The operator to use for the comparison.
*   `value`: The value to compare against.
*   `match_logic`: How to combine the conditions (`AND` or `OR`). Defaults to `AND`.

**Available Targets:**

*   `request.method`
*   `request.path`
*   `request.http_version`
*   `request.headers.<header_name>`
*   `request.body`
*   `response.status_code`
*   `response.status_message`
*   `response.headers.<header_name>`
*   `response.body`

**Available Operators:**

*   `contains`: The target string contains the value string (case-insensitive).
*   `not_contains`: The target string does not contain the value string (case-insensitive).
*   `equals`: The target string exactly matches the value string.
*   `starts_with`: The target string starts with the value string.
*   `ends_with`: The target string ends with the value string.
*   `matches_regex`: The target string matches the provided PCRE regular expression.

### Development Roadmap

This is a list of potential features and improvements for future versions:

*   **Real-time traffic interception:** Analyze traffic in real-time.
*   **User authentication:** Add user accounts and multi-user support.
*   **Rule editor UI:** A web-based UI for creating and editing tagging rules.
*   **Advanced data visualization:** Dashboards and reports for a high-level overview of the traffic.
*   **Editing and deleting records:** Manage records from the web UI.
*   **Support for other data formats:** Ingest data from formats other than CSV.

## Technical Stack

*   **Orchestration:** Docker & Docker Compose
*   **CLI & Backend:** Python 3.10+, Typer, FastAPI, PyYAML, Pymongo
*   **Database:** MongoDB 5.0+
*   **Frontend:** HTML5, CSS3, Vanilla JavaScript, Nginx
