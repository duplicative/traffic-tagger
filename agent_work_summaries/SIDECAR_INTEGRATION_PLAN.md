### **Executive Summary**

This integration strategy treats the `traffic-tagger`'s existing CSV-based HTTP records as the foundational data layer. The `sidecar-extension` will act as a powerful enrichment source, providing critical client-side context (`DOM` state, `JavaScript` execution, `Storage` events) that is impossible to capture from proxy logs alone.

The core of this plan is **correlation**. We will link the client-side events captured by the sidecar to the server-side HTTP records already stored in `traffic-tagger`, using the URL as the primary key. This will allow the rule engine to make far more intelligent and context-aware decisions, effectively bridging the gap between network traffic and browser behavior.

---

### **Phase 1: Ingesting and Storing Client-Side Events**

The goal of this phase is to establish a pipeline for getting the sidecar's non-HTTP event data into a dedicated storage area within the `traffic-tagger` ecosystem.

#### **1. Data Ingestion Strategy (Recommended: Hybrid/API)**

We will create a new, dedicated REST API endpoint on the `traffic-tagger` `api` service to receive enrichment data from the extension.

*   **Endpoint:** Create a new endpoint, such as `POST /api/enrichment-events`.
*   **Extension Modification:** Modify the `sidecar` extension's `background.js` to send **only** the `DOM_SNAPSHOT`, `JS_EXECUTION`, and `STORAGE_STATE` event types to this new endpoint. The `HTTP_TRANSACTION` data will be ignored by the extension's sending logic (or simply not sent).
*   **Workflow:** The extension will batch these client-side events and send them periodically to the API, which will then process and store them.

#### **2. Storage Strategy**

We will not modify the existing `records` collection. Instead, we will create new, separate collections in MongoDB to house the client-side event data.

*   **New Collections:**
    *   `dom_snapshots`
    *   `js_executions`
    *   `storage_states`
*   **Schema:** The schema for each collection will directly mirror the JSON structure defined in `sidecar-extension/data.md` for the corresponding `eventType`.
*   **Indexing:** To enable efficient correlation, each of these new collections must be indexed by the `url` field.

At the end of this phase, `traffic-tagger` will be passively collecting rich client-side event data and storing it, organized by URL, without yet connecting it to the existing HTTP records.

---

### **Phase 2: Correlation and Advanced Rule Application**

This phase focuses on building the logic to connect the client-side events to the HTTP records and evolving the rule engine to use this new context.

#### **1. The Correlation Engine**

The core of this phase is a new process that triggers whenever new enrichment events are ingested.

*   **Trigger:** When events arrive at the `/api/enrichment-events` endpoint and are saved, a new process is initiated.
*   **Logic:** This process takes the URL from the newly arrived event(s) and queries the main `records` collection for all existing HTTP transactions that match that URL.
*   **Action:** For each matching HTTP record found, it triggers a "re-analysis" using the enhanced rule engine.

#### **2. Rule Engine Evolution: Multi-Source Analysis**

The `shared/rule_engine.py` must be upgraded to perform context-aware analysis by querying multiple data sources.

*   **Current State:** The engine takes one HTTP record and applies rules.
*   **New State:** The engine will be modified to:
    1.  Take an HTTP record as its primary input.
    2.  Use the URL of that record to perform lookups in the new collections (`dom_snapshots`, `js_executions`, `storage_states`).
    3.  Apply a new class of "correlation rules" that can base their logic on a combination of the HTTP record *and* any client-side events associated with its URL.

#### **3. New Class of "Correlation Rules"**

This integration unlocks the ability to write significantly more powerful rules.

*   **Example Rule 1 (DOM-based XSS):**
    *   **IF** an HTTP record's response `Content-Type` is `text/html`.
    *   **AND** a `JS_EXECUTION` event exists for the same URL with `functionName: 'innerHTML'` and an `inputValue` containing script tags.
    *   **THEN** add a `potential-dom-xss` tag to the HTTP record.

*   **Example Rule 2 (Sensitive Data in Storage):**
    *   **IF** an HTTP record for a login endpoint is tagged `successful-login`.
    *   **AND** a `STORAGE_STATE` event for the subsequent URL shows a token being written to `localStorage`.
    *   **THEN** add a `token-in-localstorage` tag to the HTTP record.

---

### **Answers to Key Questions (Revised)**

*   **How to use the data from sidecar in traffic-tagger?**
    It will be used as a secondary, "enrichment" data source. The client-side events (`DOM`, `JS`, `Storage`) will be correlated with the existing HTTP records by URL to provide a more complete picture of potential vulnerabilities.

*   **Should the schema be modified?**
    The existing `records` schema for HTTP transactions can remain largely unchanged. However, the system must be expanded with **new schemas and collections** to store the different types of client-side events from the sidecar.

*   **Should the traffic-tagger processing engine be modified?**
    Yes, this is the most critical change. The rule engine must evolve from analyzing a single HTTP record to a "correlation engine" that can query across multiple collections (the main HTTP records plus the new client-side event collections) to apply advanced, context-aware rules.
