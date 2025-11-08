### **Feature: User Input Reflection Analysis in Timeline View**

**Objective:** To automatically identify when user-controlled data from an HTTP request is reflected in subsequent client-side events (DOM, JS execution, storage) and display an indicator in the Timeline UI.

---

### **Phase 1: Create a User Input Extraction Module**

This foundational component will be responsible for identifying and extracting all potential user-controlled data from a raw HTTP request.

*   **Create a new file:** `shared/user_input_extractor.py`.
*   **Implement `extract_inputs(decoded_request)` function:**
    *   **Input:** The full decoded HTTP request string.
    *   **Logic:**
        1.  Parse the request to identify the path, query string, headers, and body.
        2.  **Query String:** Split the query string into key-value pairs. Add all values to a list of potential user inputs.
        3.  **Request Body:**
            *   Check the `Content-Type` header.
            *   Support `application/x-www-form-urlencoded`: Parse the body into key-value pairs and add the values to the list.
            *   Support `application/json`: Parse the JSON body and recursively extract all string values.
            *   Support `multipart/form-data`: Parse the different parts and extract values.
        4.  **Cookies:** Parse the `Cookie` header and add cookie values to the list.
    *   **Output:** A deduplicated list of strings representing all identified user inputs.

---

### **Phase 2: Develop the Reflection Analysis Engine**

This is the core logic engine that will correlate the extracted user inputs with the sidecar events.

*   **Create a new file:** `shared/reflection_analyzer.py`.
*   **Implement `analyze_reflections(http_record, sidecar_events)` function:**
    *   **Input:** A single parent HTTP record from the database and a list of its associated child sidecar events.
    *   **Logic:**
        1.  Call the `user_input_extractor.extract_inputs()` function with the `decoded_request` from the HTTP record to get the list of user inputs.
        2.  Initialize an empty list called `reflected_values`.
        3.  Iterate through each `user_input` string from the list.
        4.  For each input, iterate through every `sidecar_event` in the list.
        5.  Search for the `user_input` string within the relevant data fields of the sidecar event:
            *   **`dom_snapshots`:** Search within the `eventData.dom` field.
            *   **`js_executions`:** Search within the `eventData.script` field.
            *   **`storage_states`:** Search within the `eventData.value` field.
        6.  If a match is found and the value isn't already in `reflected_values`, add it. The search should be case-insensitive and handle variations (e.g., URL-decoded vs. raw values).
    *   **Output:** The `reflected_values` list.

---

### **Phase 3: Backend API Integration**

This phase involves integrating the new analysis engine into the existing API that powers the timeline.

*   **Modify the file:** `api/main.py`.
*   **Update the `GET /api/timeline` endpoint:**
    *   Import the new `analyze_reflections` function.
    *   After the existing logic fetches and correlates the HTTP records with their sidecar events, iterate through each parent HTTP record.
    *   For each record, call `analyze_reflections(record, associated_sidecar_events)`.
    *   Store the result in a new key within the record object, e.g., `record['reflections'] = reflected_values`.
    *   Ensure the API response now includes this new `reflections` field for each HTTP record. The field will be an empty list if no reflections are found.

---

### **Phase 4: Frontend UI Implementation**

Finally, this phase will make the analysis results visible to the user in the web interface.

*   **Modify the file:** `frontend/static/app.js`.
*   **Update the timeline rendering logic:**
    *   In the function that processes the response from `GET /api/timeline`, check for the new `reflections` key for each record.
    *   Modify the function that generates the HTML for the collapsible record header.
    *   If `record.reflections` is not empty, add a visual indicator to the header. This could be a specific icon (e.g., a "reflect" or "echo" icon) and/or a styled text badge like `[Reflected Input]`.
    *   **Add a tooltip:** When the user hovers over the new indicator, a tooltip should appear that lists the specific values found in the `record.reflections` array, giving the user immediate context on what was reflected.
