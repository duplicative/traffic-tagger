# **Product Requirements Document: User Input Reflection Analysis Engine**

## **1. Overview**

**Feature:** User Input Reflection Analysis in Timeline View
**Project:** Traffic Tagger
**Objective:** To automatically detect and visualize instances where user-controlled data from an HTTP request is "reflected" back in associated client-side events. This provides a powerful, automated way to spot potential Cross-Site Scripting (XSS) and other data handling vulnerabilities directly within the Timeline interface.

## **2. Functional Requirements**

This feature will be implemented in four distinct phases, building upon the existing project structure.

### **Phase 1: User Input Extraction Module**

**Goal:** Create a reusable Python module capable of identifying and extracting all potential user-controlled data from a raw HTTP request.

**File to Create:** `shared/user_input_extractor.py`

**Implementation Details:**
- Create a primary function: `extract_inputs(decoded_request: str) -> list[str]`.
- This function must parse the `decoded_request` string. You can leverage the existing `shared/http_parser.py` if helpful, but the logic should be self-contained for this specific task.
- **Extraction Targets:**
    1.  **URL Query Parameters:** For a URL like `/?id=123&name=test`, extract `123` and `test`.
    2.  **Request Body (`application/x-www-form-urlencoded`):** For a body like `user=admin&pass=secret`, extract `admin` and `secret`.
    3.  **Request Body (`application/json`):** Recursively traverse the JSON and extract all string values.
    4.  **Cookie Values:** Parse the `Cookie:` header and extract the values of all cookies.
- The function must return a list of unique strings.

---

### **Phase 2: Reflection Analysis Engine**

**Goal:** Create the core analysis engine that compares user inputs against sidecar event data to find reflections.

**File to Create:** `shared/reflection_analyzer.py`

**Implementation Details:**
- **Import:** `from shared.user_input_extractor import extract_inputs`.
- **Create a primary function:** `analyze_reflections(http_record: dict, sidecar_events: list[dict]) -> list[str]`.
- **Logic:**
    1.  Call `extract_inputs` on the `http_record['decoded_request']` to get a list of user inputs.
    2.  Iterate through each user input string.
    3.  For each input, perform a case-insensitive search within every sidecar event provided.
    4.  **Search Locations within `sidecar_events`:**
        - If `eventType` is `DOM_SNAPSHOT`, search in `eventData['dom']`.
        - If `eventType` is `JS_EXECUTION`, search in `eventData['script']`.
        - If `eventType` is `STORAGE_STATE`, search in `eventData['value']`.
    5.  Collect all unique user inputs that are found within the sidecar events.
- **Return Value:** The function must return a list of the reflected strings.

---

### **Phase 3: Backend API Integration**

**Goal:** Integrate the reflection analysis into the existing `/api/timeline` endpoint.

**File to Modify:** `api/main.py`

**Implementation Details:**
- **Import:** `from shared.reflection_analyzer import analyze_reflections`.
- Locate the `get_timeline()` function that handles the `GET /api/timeline` request.
- After the function has fetched and grouped the HTTP records with their corresponding sidecar events, perform the following steps:
    1.  Iterate through the list of parent HTTP records.
    2.  For each `record`, call `analyze_reflections(record, record['sidecar_events'])`.
    3.  Add a new key-value pair to the record dictionary: `record['reflections'] = result_from_analyzer`.
- The final JSON response for each record in the timeline must now include the `reflections` field (which will be an empty list if no reflections were found).

---

### **Phase 4: Frontend UI Implementation**

**Goal:** Display a clear visual indicator in the UI when input reflections are detected.

**File to Modify:** `frontend/static/app.js`

**Implementation Details:**
- Locate the JavaScript function responsible for fetching data from `/api/timeline` and rendering the timeline view (likely named similar to `loadTimeline` or `renderTimeline`).
- In the loop that renders each collapsible HTTP record header, add a conditional check:
    - `if (record.reflections && record.reflections.length > 0)`
- **If the condition is true:**
    1.  **Add a Visual Indicator:** Append a new HTML element to the record's header. This should be an icon or a text badge.
        - **Example HTML:** `<span class="reflection-badge" title="">[Input Reflected]</span>`
    2.  **Populate the Tooltip:** Dynamically set the `title` attribute of the new element to a descriptive string.
        - **Example Tooltip Text:** `"Reflected Values: [value1], [value2]"`
        - Join the `record.reflections` array with `, ` to create this text.
- **Add CSS Styling:**
    - Open `frontend/static/styles.css`.
    - Create a new style for the `.reflection-badge` class.
    - **Example CSS:**
      ```css
      .reflection-badge {
        background-color: #ff4d4d; /* A bright, attention-grabbing color */
        color: white;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8em;
        margin-left: 10px;
        font-weight: bold;
      }
      ```

## **3. Acceptance Criteria**

- **AC-1:** When an HTTP request's query parameter is found inside a subsequent `DOM_SNAPSHOT` event, the reflection badge must appear on its timeline entry.
- **AC-2:** When a value from a JSON request body is found inside a `JS_EXECUTION` event's script content, the reflection badge must appear.
- **AC-3:** When a cookie value is found inside a `STORAGE_STATE` event, the reflection badge must appear.
- **AC-4:** If no user inputs are found in any sidecar events, no badge should be displayed.
- **AC-5:** Hovering over the reflection badge must display a tooltip listing the exact strings that were reflected.
- **AC-6:** The existing functionality of the timeline (expanding/collapsing, viewing details) must remain unaffected.
