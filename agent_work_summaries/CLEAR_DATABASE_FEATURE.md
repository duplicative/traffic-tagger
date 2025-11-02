# Clear Database Feature

**Date:** 2025-11-01  
**Feature:** Clear all database records from frontend  
**Status:** ✅ COMPLETE

## Overview

Added functionality to clear all records from the database via the frontend UI. This allows users to start fresh analysis with new CSV data without having previous data still in the database.

## Changes Made

### 1. API Endpoint: `DELETE /api/clear-all`

**Location:** `api/main.py`

**Functionality:**
- Deletes all records from all collections in the database
- Returns detailed count of deleted records per collection
- Includes error handling and proper HTTP status codes

**Collections Cleared:**
1. `records` - HTTP traffic records from CSV ingestion
2. `dom_snapshots` - Client-side DOM events
3. `js_executions` - Client-side JavaScript execution events
4. `storage_states` - Client-side storage events
5. `watcher_metadata` - Watcher service tracking data

**Response Format:**
```json
{
  "status": "success",
  "message": "Cleared 948 total records from database",
  "details": {
    "records": 943,
    "dom_snapshots": 2,
    "js_executions": 1,
    "storage_states": 1,
    "watcher_metadata": 1
  }
}
```

### 2. Frontend Implementation

**Modified Files:**
- `frontend/static/app.js` - Added `clearDatabase()` function
- `frontend/static/index.html` - Updated button text

**Button Changes:**
- **Previous:** "Clear All" (only cleared filters)
- **Current:** "Clear Database" (clears entire database)
- **Tooltip:** "Clear all records from database"

**User Experience:**

1. **Confirmation Dialog:**
   ```
   Are you sure you want to clear ALL records from the database?

   This will permanently delete:
   • All HTTP traffic records
   • All client-side enrichment events
   • All watcher metadata

   This action CANNOT be undone!
   ```

2. **Loading State:**
   - Shows "Clearing database..." message while processing

3. **Success Notification:**
   - Shows detailed breakdown of deleted records per collection
   - Automatically reloads tags (will be empty)
   - Updates UI to show "Database cleared" message

4. **Error Handling:**
   - Shows user-friendly error messages
   - Logs detailed errors to console

### 3. Frontend Function: `clearDatabase()`

**Location:** `frontend/static/app.js` (Lines 128-187)

**Workflow:**
1. Show confirmation dialog with warning
2. If confirmed, show loading state
3. Call `DELETE /api/clear-all` endpoint
4. Parse response and show success details
5. Clear local state (selected tags, records, expanded records)
6. Reload tags from API
7. Update UI with empty state message

## Usage

### Via Web UI

1. Open traffic-tagger UI: http://localhost:9999/
2. Click "Clear Database" button in the left sidebar
3. Confirm the action in the popup dialog
4. Wait for completion message
5. Import new CSV data to start fresh analysis

### Via API (cURL)

```bash
curl -X DELETE http://localhost:8000/api/clear-all
```

### Via Python Script

```bash
python test_clear_database.py
```

## Testing

**Test Script:** `test_clear_database.py`

**Test Coverage:**
- ✅ Shows current database state before clearing
- ✅ Requires explicit confirmation ("YES")
- ✅ Calls API endpoint and handles response
- ✅ Verifies database is empty after clearing
- ✅ Shows detailed breakdown of deleted records

**Manual Test:**
1. Ensure database has records (import CSV if needed)
2. Open web UI at http://localhost:9999/
3. Click "Clear Database" button
4. Confirm in dialog
5. Verify success message shows correct counts
6. Verify tags list is now empty
7. Verify records area shows "Database cleared" message

## Safety Features

1. **Double Confirmation:**
   - Browser confirmation dialog with explicit warning
   - Clear description of what will be deleted

2. **Visual Feedback:**
   - Loading state during operation
   - Detailed success message with counts
   - UI automatically updates to reflect empty state

3. **Error Handling:**
   - API errors are caught and displayed
   - Network errors are handled gracefully
   - Console logging for debugging

4. **No Accidental Clicks:**
   - Button clearly labeled "Clear Database"
   - Tooltip explains functionality
   - Warning dialog prevents accidental confirmation

## Use Cases

### Scenario 1: New Analysis Session
User wants to analyze traffic from a new target application without old data interfering.

**Steps:**
1. Click "Clear Database"
2. Confirm deletion
3. Drop new CSV file in `data/` directory
4. New analysis starts with clean slate

### Scenario 2: Testing Rules
User wants to test new tagging rules on same CSV without duplicates.

**Steps:**
1. Clear database
2. Modify `data/rules.yaml`
3. Re-ingest same CSV (watcher will process it again)
4. Fresh tags applied without old data

### Scenario 3: Space Management
User wants to free up database space before starting large import.

**Steps:**
1. Clear database to remove old data
2. Import new large dataset
3. Database has room for new data

## Implementation Details

### API Endpoint

```python
@app.delete("/api/clear-all")
async def clear_all_records():
    """Clear all records from all collections in the database."""
    try:
        deleted_counts = {}
        collections_to_clear = [
            "records",
            "dom_snapshots",
            "js_executions",
            "storage_states",
            "watcher_metadata"
        ]
        
        total_deleted = 0
        for collection_name in collections_to_clear:
            collection = db[collection_name]
            result = collection.delete_many({})
            deleted_counts[collection_name] = result.deleted_count
            total_deleted += result.deleted_count
        
        return {
            "status": "success",
            "message": f"Cleared {total_deleted} total records from database",
            "details": deleted_counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing database: {str(e)}")
```

### Frontend Function (Summary)

```javascript
async function clearDatabase() {
    // 1. Show confirmation dialog
    const confirmed = confirm('Are you sure...');
    if (!confirmed) return;
    
    // 2. Call API
    const response = await fetch(`${API_BASE}/clear-all`, {
        method: 'DELETE'
    });
    
    // 3. Handle response
    const data = await response.json();
    alert(`Database cleared successfully!\n\n${data.message}`);
    
    // 4. Update UI
    state.selectedTags.clear();
    await loadTags();
    // ... more UI updates
}
```

## Known Limitations

1. **No Undo:** Once cleared, data cannot be recovered (except from CSV backups)
2. **No Selective Delete:** Clears all collections, no option to keep some data
3. **No Backup:** Does not create automatic backup before clearing
4. **Single Confirmation:** Only one confirmation dialog (not double-confirm)

## Future Enhancements

Potential improvements for future versions:

1. **Backup Before Clear:** Automatically export data before clearing
2. **Selective Clearing:** Options to clear only certain collections
3. **Clear by Date Range:** Delete records older than X days
4. **Clear by Tag:** Delete only records with specific tags
5. **Progress Indicator:** Show real-time progress for large databases
6. **Audit Log:** Record who cleared database and when

## Troubleshooting

### Button Not Working
- **Check:** Browser console for JavaScript errors
- **Solution:** Reload page, clear browser cache

### API Returns Error
- **Check:** API logs with `docker compose logs api`
- **Solution:** Restart API container

### Database Not Clearing
- **Check:** MongoDB connection in API
- **Solution:** Verify MongoDB is running: `docker compose ps`

### UI Still Shows Old Data
- **Check:** Browser may have cached data
- **Solution:** Hard refresh (Ctrl+Shift+R) or clear browser cache

## Files Modified

- `api/main.py` - Added DELETE /api/clear-all endpoint
- `frontend/static/app.js` - Added clearDatabase() function
- `frontend/static/index.html` - Updated button text and tooltip
- `test_clear_database.py` - Created test script (new file)

## Deployment

To deploy these changes:

```bash
# Rebuild containers
docker compose build api frontend

# Restart services
docker compose up -d api frontend

# Verify API is running
curl http://localhost:8000/

# Test clear endpoint (WARNING: will clear data!)
curl -X DELETE http://localhost:8000/api/clear-all
```

## Conclusion

The Clear Database feature provides users with a safe and efficient way to remove all records from the database, enabling fresh analysis sessions without interference from previous data. The feature includes appropriate safeguards (confirmation dialogs) while remaining simple and accessible through the web UI.
