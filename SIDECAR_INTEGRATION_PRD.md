# PRD: Sidecar Extension Integration for Traffic Tagger

**Version:** 1.0
**Status:** Draft

## 1. Overview

This document outlines the requirements for integrating the `sidecar-extension` with the `traffic-tagger` application. The goal is not to replace the existing data pipeline but to **enrich** it. 

The current `traffic-tagger` system analyzes HTTP records ingested from CSV files. This project will enhance its capabilities by introducing a new stream of data from the `sidecar-extension`, which captures client-side browser events. By correlating the existing HTTP records with these new client-side events (like DOM changes and JavaScript execution), the `traffic-tagger`'s rule engine will be able to identify more complex and subtle vulnerabilities.

## 2. Goals and Objectives

- **Primary Goal:** To augment existing HTTP records with client-side context captured by the `sidecar-extension`.
- **Secondary Goal:** To upgrade the `traffic-tagger` rule engine to support "correlation rules" that analyze data from multiple sources (HTTP records and client-side events).
- **Business Outcome:** Increase the accuracy and scope of the security analysis, enabling the detection of vulnerabilities like DOM-based XSS and insecure client-side storage patterns that are invisible to a simple proxy.

## 3. Scope

### In Scope

-   **API Modification:** A new API endpoint will be added to the `api` service to ingest client-side events.
-   **Database Modification:** Three new collections will be created in MongoDB to store the new event types.
-   **Extension Modification:** The `sidecar-extension` will be modified to send only non-HTTP events to the new API endpoint.
-   **Rule Engine Evolution:** The `shared/rule_engine.py` will be significantly updated to query the new collections and apply correlation rules.
-   **Correlation Logic:** A new mechanism will be built to trigger re-analysis of HTTP records when new, relevant client-side data arrives.

### Out of Scope

-   **No UI Changes:** This is a backend-only project. The `traffic-tagger` frontend will not be modified to visualize the new data.
-   **No HTTP Data Duplication:** The integration will **not** ingest `HTTP_TRANSACTION` events from the sidecar. The existing CSV import process remains the sole source for HTTP records.
-   **No `watcher` service changes:** The `watcher` service will not be modified.

## 4. Functional Requirements

This project is divided into two main phases of implementation.

### Phase 1: Ingesting and Storing Client-Side Events

#### FR 1.1: Modify `sidecar-extension` to Send Enrichment Data

-   **File to Modify:** `sidecar-extension/background.js`
-   **Logic:**
    1.  The existing WebSocket connection logic (`BackendConnection` class) should be disabled or modified.
    2.  A new function, e.g., `sendEnrichmentData(events)`, will be created. This function will send a batch of events to the new `traffic-tagger` API endpoint using a `fetch` POST request.
    3.  The `chrome.runtime.onMessage` listener must be modified. For messages of type `DOM_SNAPSHOT`, `JS_EXECUTION`, and `STORAGE_STATE`, the resulting event object should be batched and sent via the new `sendEnrichmentData` function.
    4.  The logic that generates and sends `HTTP_TRANSACTION` events must be disabled to prevent it from being sent.

#### FR 1.2: Create Enrichment API Endpoint in `traffic-tagger`

-   **File to Modify:** `api/main.py`
-   **Requirement:** Create a new FastAPI endpoint `POST /api/enrichment-events`.
-   **Request Body:** The endpoint must accept a JSON body containing a list of event objects.
-   **Logic:**
    1.  The endpoint will receive a list of events.
    2.  It will iterate through each event in the list.
    3.  Based on the `eventType` field (`DOM_SNAPSHOT`, `JS_EXECUTION`, or `STORAGE_STATE`), it will save the event object to the corresponding new MongoDB collection.
    4.  After saving the events, it will trigger the correlation logic defined in Phase 2.

#### FR 1.3: Create New Database Collections

-   **Action:** In MongoDB, create three new collections:
    1.  `dom_snapshots`
    2.  `js_executions`
    3.  `storage_states`
-   **Indexes:** An index must be created on the `url` field for each of these three new collections to ensure efficient lookups.

### Phase 2: Correlation and Advanced Rule Application

#### FR 2.1: Implement the Correlation Engine

-   **Location:** This logic will be implemented within the `POST /api/enrichment-events` endpoint in `api/main.py`, to be executed after new events are successfully stored.
-   **Logic:**
    1.  For each event saved in FR 1.2, get its `url`.
    2.  Query the main `records` collection in MongoDB to find all documents where the `url` field is an exact match.
    3.  For each matching HTTP record found, invoke a new method in the `RuleEngine` to perform re-analysis (e.g., `rule_engine.run_correlation_analysis(record)`).

#### FR 2.2: Evolve the Rule Engine for Multi-Source Analysis

-   **File to Modify:** `shared/rule_engine.py`
-   **Requirement:** The `RuleEngine` class must be refactored to support querying the new collections.
-   **Implementation:**
    1.  The `RuleEngine` should be initialized with a MongoDB database client instance to allow it to access collections.
    2.  Create a new method, e.g., `run_correlation_analysis(http_record)`.
    3.  Inside this method, implement logic for a new class of rules. These rules will use the `http_record`'s URL to query the `dom_snapshots`, `js_executions`, and `storage_states` collections.
    4.  If a correlation rule's conditions are met, the method will update the `tags` field of the original `http_record` in the `records` collection.

## 5. Data Models and Storage

The new collections will store documents matching the schemas from `sidecar-extension/data.md`.

#### `dom_snapshots` Collection Schema:
```json
{
  "eventId": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "eventType": "DOM_SNAPSHOT",
  "url": "string",
  "data": {
    "html": "string",
    "mutations": ["string"]
  }
}
```

#### `js_executions` Collection Schema:
```json
{
  "eventId": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "eventType": "JS_EXECUTION",
  "url": "string",
  "data": {
    "functionName": "string",
    "inputValue": "string",
    "stackTrace": "string"
  }
}
```

#### `storage_states` Collection Schema:
```json
{
  "eventId": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "eventType": "STORAGE_STATE",
  "url": "string",
  "data": {
    "localStorage": { "key": "value", ... },
    "sessionStorage": { "key": "value", ... },
    "cookies": [
      { "name": "string", "value": "string" }
    ]
  }
}
```

## 6. Acceptance Criteria

-   **AC-1:** When a user browses a website with the modified `sidecar-extension`, `DOM_SNAPSHOT`, `JS_EXECUTION`, and `STORAGE_STATE` events are successfully received by the `POST /api/enrichment-events` endpoint.
-   **AC-2:** The received events are correctly stored in their respective MongoDB collections (`dom_snapshots`, `js_executions`, `storage_states`).
-   **AC-3:** The `HTTP_TRANSACTION` events from the sidecar are **not** sent to the API and **not** stored in the database.
-   **AC-4:** A new correlation rule is defined in `rules.yaml` (e.g., one that checks for `innerHTML` execution on a specific URL).
-   **AC-5:** When an HTTP record (from a CSV import) and a client-side event are both present and match the conditions of the new correlation rule, the `tags` array of that HTTP record in the `records` collection is correctly updated with the new tag.
-   **AC-6:** The existing functionality of ingesting and processing data from CSV files remains unaffected.
