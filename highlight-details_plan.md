### Plan for Highlight Integration

1.  **Rule Engine (`shared/rule_engine.py`):**
    *   Modify the `evaluate` function in the `RuleEngine` class. Instead of just returning `True` on a match, it will now return a list of the specific string values from the request or response that caused the rule to match. If there is no match, it will return an empty list.

2.  **Data Storage (MongoDB):**
    *   The data structure for a record in MongoDB will be updated. A new field, `highlights`, will be added. This field will store an object where keys are rule names and values are the list of strings that matched the rule's conditions.

3.  **Data Ingestion (`cli/main.py` & `watcher/main.py`):**
    *   The data ingestion scripts will be updated to use the modified rule engine.
    *   When a rule matches, the returned list of matched values will be stored in the `highlights` field of the corresponding record in MongoDB.

4.  **API (`api/main.py`):**
    *   The `/api/record/{record_id}` endpoint will be updated to include the `highlights` field in the JSON response.

5.  **Frontend (`frontend/static/app.js`):**
    *   The `loadRecordDetails` function will be modified to process the new `highlights` field from the API response.
    *   A new function will be created to take the raw request/response text and the `highlights` data. This function will wrap the matched substrings in `<span>` elements with a specific CSS class for highlighting.
    *   The updated text with the `<span>` tags will be displayed in the UI.

6.  **Frontend Styling (`frontend/static/styles.css`):**
    *   A new CSS rule will be added to style the highlight `<span>` elements, for example, by giving them a yellow background.
