# Sidecar Extension Data Collection

This document outlines the data collected by the Sidecar browser extension, its schema, and the overall data flow.

## Data Objects

The extension collects four main types of data objects.

### 1. HTTP Transaction

*   **Description:** This object captures a complete HTTP request and its corresponding response. It is used to analyze network traffic to and from the monitored web application.
*   **Collection:** The extension uses the `chrome.debugger` API to attach to a tab and intercept network events. It listens for `Network.requestWillBeSent`, `Network.responseReceived`, and `Network.loadingFinished` to assemble the full transaction.
*   **Schema:**
    ```json
    {
      "eventId": "string (UUID)",
      "timestamp": "string (ISO 8601)",
      "eventType": "HTTP_TRANSACTION",
      "url": "string",
      "data": {
        "request": {
          "method": "string",
          "url": "string",
          "headers": [
            { "name": "string", "value": "string" }
          ],
          "body": "string | null"
        },
        "response": {
          "statusCode": "integer",
          "statusText": "string",
          "headers": [
            { "name": "string", "value": "string" }
          ],
          "body": "string | null"
        }
      }
    }
    ```
*   **Example:**
    ```json
    {
      "eventId": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
      "timestamp": "2025-10-31T10:00:00.000Z",
      "eventType": "HTTP_TRANSACTION",
      "url": "https://example.com/api/data",
      "data": {
        "request": {
          "method": "POST",
          "url": "https://example.com/api/data",
          "headers": [
            { "name": "Content-Type", "value": "application/json" }
          ],
          "body": "{\"key\":\"value\"}"
        },
        "response": {
          "statusCode": 200,
          "statusText": "OK",
          "headers": [
            { "name": "Content-Type", "value": "application/json" }
          ],
          "body": "{\"success\":true}"
        }
      }
    }
    ```

### 2. DOM Snapshot

*   **Description:** This object contains a snapshot of the page's DOM (Document Object Model) at a specific moment. It is used to identify potential DOM-based XSS vulnerabilities and other client-side issues.
*   **Collection:** A content script (`content-script.js`) is injected into the page. It captures the initial DOM on load and then uses a `MutationObserver` to detect and send subsequent changes.
*   **Schema:**
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
*   **Example:**
    ```json
    {
      "eventId": "b2c3d4e5-f6a7-8901-2345-67890abcdef1",
      "timestamp": "2025-10-31T10:00:05.000Z",
      "eventType": "DOM_SNAPSHOT",
      "url": "https://example.com",
      "data": {
        "html": "<html>...</html>",
        "mutations": ["initial"]
      }
    }
    ```

### 3. JavaScript Execution

*   **Description:** This object logs the execution of potentially dangerous JavaScript functions (sinks) that could be exploited for XSS, such as `eval()`, `innerHTML`, and `document.write()`.
*   **Collection:** A script (`interceptor.js`) is injected into the main world of the web page. This script hooks and reports calls to these sensitive functions. The data is sent from the interceptor to the content script, and then to the background script.
*   **Schema:**
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
*   **Example:**
    ```json
    {
      "eventId": "c3d4e5f6-a7b8-9012-3456-7890abcdef12",
      "timestamp": "2025-10-31T10:00:10.000Z",
      "eventType": "JS_EXECUTION",
      "url": "https://example.com/page",
      "data": {
        "functionName": "innerHTML",
        "inputValue": "<img src=x onerror=alert(1)>",
        "stackTrace": "Error\n    at reportExecution (chrome-extension://.../interceptor.js:23:23)\n    ..."
      }
    }
    ```

### 4. Storage State

*   **Description:** This object captures the state of the browser's storage, including `localStorage`, `sessionStorage`, and cookies. This is useful for identifying sensitive information stored on the client-side.
*   **Collection:** The content script (`content-script.js`) periodically polls for storage changes and sends a complete snapshot if any modifications are detected.
*   **Schema:**
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
*   **Example:**
    ```json
    {
      "eventId": "d4e5f6a7-b8c9-0123-4567-890abcdef123",
      "timestamp": "2025-10-31T10:00:15.000Z",
      "eventType": "STORAGE_STATE",
      "url": "https://example.com",
      "data": {
        "localStorage": {
          "user_token": "xyz123"
        },
        "sessionStorage": {},
        "cookies": [
          { "name": "session_id", "value": "abc987" }
        ]
      }
    }
    ```

## Data Flow

1.  **Data Collection in the Browser:**
    *   **HTTP Transactions** are captured by the background script (`background.js`) using the `chrome.debugger` API.
    *   **DOM Snapshots**, **JS Executions**, and **Storage State** are collected by scripts injected into the web page (`content-script.js` and `interceptor.js`).

2.  **Processing within the Extension:**
    *   The collected data is not significantly processed within the extension. It is formatted into one of the four JSON object types described above.
    *   The background script acts as a central hub, receiving data from the content scripts and the debugger API.
    *   A `message-logger.js` component logs each event to `chrome.storage.local` for debugging and potential download by the user.

3.  **Data Exfiltration:**
    *   The primary way data leaves the extension is by being sent to a configurable backend server over a WebSocket connection.
    *   The `background.js` script establishes and maintains this WebSocket connection. If the connection is down, events are queued until it is re-established.

4.  **User Configuration:**
    *   The user can change the destination of the data by configuring the backend server's IP address and port.
    *   This is done through the extension's settings page (`settings.html` and `settings.js`), which saves the configuration to `chrome.storage.sync`.
    *   The user can also download the collected logs directly from the extension via the popup UI, which triggers the `messageLogger.downloadLogs()` function.

In summary, the extension acts as a data collector and forwarder. It gathers security-relevant events from the browser, formats them, and sends them to a user-defined backend for further analysis, while also providing an option for local logging and download.
