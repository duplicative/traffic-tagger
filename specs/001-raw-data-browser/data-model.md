# Data Model: Raw Data Browser

**Date**: 2025-11-02

This document describes the data models for the records that will be displayed in the Raw Data Browser.

## Record Types

There are two main types of records that will be displayed:

1.  **HTTP Records (from CSV)**: These are the existing records in the `records` collection.
2.  **Enrichment Records (from Sidecar)**: These are the new records from the `dom_snapshots`, `js_executions`, and `storage_states` collections.

## HTTP Record Schema

This is the existing schema for records in the `records` collection.

```json
{
  "_id": "ObjectId",
  "request": "string",
  "response": "string",
  "host": "string",
  "path": "string",
  "method": "string",
  "response_status_code": "integer",
  "tags": ["string"],
  "highlights": {
    "tag_name": ["string"]
  },
  "decoded_request": "string",
  "decoded_response": "string"
}
```

## Enrichment Record Schemas

These schemas are based on the `SIDECAR_INTEGRATION_PRD.md` document.

### `dom_snapshots` Collection Schema:
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

### `js_executions` Collection Schema:
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

### `storage_states` Collection Schema:
```json
{
  "eventId": "string (UUID)",
  "timestamp": "string (ISO 8601)",
  "eventType": "STORAGE_STATE",
  "url": "string",
  "data": {
    "localStorage": { "key": "value" },
    "sessionStorage": { "key": "value" },
    "cookies": [
      { "name": "string", "value": "string" }
    ]
  }
}
```
