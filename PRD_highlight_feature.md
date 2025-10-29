# Product Requirements Document: Highlight Matched Rule Values

## 1. Feature Overview

**Feature:** Highlight Matched Rule Values in UI

**Objective:** To enhance the user experience by visually highlighting the specific parts of an HTTP request or response that trigger a rule match. This allows analysts to immediately focus on the most relevant data within a traffic record.

**User Benefit:** Reduces the time and effort required to manually search for the data that caused a tag to be applied, leading to faster analysis and identification of interesting traffic patterns.

---

## 2. Scope

This feature implementation spans the entire application stack:

*   **Backend:** Rule Engine, Data Ingestion (CLI & Watcher), and API.
*   **Database:** MongoDB data schema.
*   **Frontend:** JavaScript application logic and CSS styling.

---

## 3. Detailed Requirements & Implementation Plan

The development will be executed by modifying specific files as detailed below.

### Task 1: Enhance the Rule Engine

*   **File:** `shared/rule_engine.py`
*   **Goal:** Modify the rule engine to return the specific values that cause a rule to match, instead of a simple boolean.
*   **Action:**
    1.  Locate the `evaluate` function within the `RuleEngine` class.
    2.  Change its return type. Instead of returning `True` upon a successful match, it must return a `list` of the actual string values that were matched.
    3.  For operators like `contains` or `matches_regex`, the function should return the substring from the target field (e.g., `request.body`) that matched the condition's value. For other operators, returning the condition's `value` may be sufficient.
    4.  If a rule's conditions are not met, the function must return an empty list (`[]`).

### Task 2: Update the Data Storage Model

*   **Goal:** Update the MongoDB record structure to store the matched highlight data.
*   **Action:**
    1.  A new field named `highlights` will be added to the main record schema.
    2.  This field will be a dictionary (or object) where each key is the `name` of a matched rule, and the value is the `list` of matched strings returned by the `evaluate` function from Task 1.
    *   **Example Structure:**
        ```json
        {
          "tags": ["Potential PII Leak", "API Call"],
          "highlights": {
            "Potential PII Leak": ["ssn: 123-456-7890"],
            "API Call": ["/api/v1/users"]
          },
          ...
        }
        ```

### Task 3: Modify Data Ingestion Logic

*   **Files:** `cli/main.py` and `watcher/main.py`
*   **Goal:** Update the data ingestion and processing logic to use the enhanced rule engine and store the highlights.
*   **Action:**
    1.  In both the CLI and Watcher ingestion flows, when iterating through rules for a given record, capture the list of matched values returned by the modified `rule_engine.evaluate()` function.
    2.  If the returned list is not empty (i.e., the rule matched), populate the `highlights` dictionary for the record as described in Task 2.
    3.  When inserting or updating the record in MongoDB, ensure the new `highlights` field is included. This applies to initial CSV ingestion, re-tagging operations, and hot-reloading of rules.

### Task 4: Expose Highlights via the API

*   **File:** `api/main.py`
*   **Goal:** Make the `highlights` data available to the frontend.
*   **Action:**
    1.  Locate the `/api/record/{record_id}` endpoint.
    2.  Modify the response model to include the `highlights` field from the MongoDB document. The API should return this field as part of the JSON payload for a single record.

### Task 5: Implement Frontend Highlighting

*   **File:** `frontend/static/app.js`
*   **Goal:** Use the `highlights` data from the API to visually mark up the request and response text in the UI.
*   **Action:**
    1.  In the `loadRecordDetails` function, after fetching the record data, check for the presence of the `highlights` field.
    2.  Create a new helper function, e.g., `applyHighlights(text, highlights)`.
    3.  This function will take the raw text (`decoded_request` or `decoded_response`) and the `highlights` object as input.
    4.  Inside this function, iterate through all the matched string values in the `highlights` object. For each matched string, find it in the raw text and wrap it in a `<span>` element with a dedicated class (e.g., `<span class="highlight">matched_string</span>`).
    5.  **Important:** The replacement must be done carefully to handle special characters and avoid breaking the HTML structure. A global string replacement for each highlight is the recommended approach.
    6.  In `loadRecordDetails`, call this new helper function on both the request and response text before rendering them to the screen.

### Task 6: Add CSS Styling for Highlights

*   **File:** `frontend/static/styles.css`
*   **Goal:** Define the visual appearance of the highlighted text.
*   **Action:**
    1.  Add a new CSS rule for the `.highlight` class.
    2.  Set a distinct background color to make the highlights easily visible. A yellow background is recommended for high contrast.
    *   **Example CSS:**
        ```css
        .highlight {
          background-color: yellow;
          color: black; /* Ensure text is readable */
        }
        ```

---

## 4. Acceptance Criteria

*   When a rule matches a record, the specific matching text is correctly stored in the record's `highlights` field in MongoDB.
*   The `/api/record/{record_id}` endpoint successfully returns the `highlights` object for records that have them.
*   When viewing a record's details in the web UI, all matched text in the request and response sections is highlighted with a yellow background.
*   If a record has no matching rules or a rule match produces no specific highlight, no text is highlighted and no errors occur.
*   All existing functionality, including tagging, filtering by tags, and data ingestion, continues to work as expected.
