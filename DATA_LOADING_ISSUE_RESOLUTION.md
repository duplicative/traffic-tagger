# Data Loading Issue Investigation & Resolution

**Date:** 2025-11-01  
**Issue:** Application displaying TestTag1/TestTag2 instead of actual CSV data  
**Status:** ✅ RESOLVED

## Problem Summary

The traffic-tagger UI was showing only "TestTag1" and "TestTag2" instead of the actual tags from the `hex-tech2025-11-01.csv` file. When clicked, tags showed "Error loading records."

## Root Cause Analysis

### Investigation Steps

1. **Check Database State:**
   - Only 1 record in database with tags: TestTag1, TestTag2
   - Expected: 909 records from hex-tech2025-11-01.csv

2. **Check Data Directory:**
   - ✅ hex-tech2025-11-01.csv exists (40MB)
   - ✅ rules.yaml exists (12KB)

3. **Check Watcher Logs:**
   - Watcher had successfully processed CSV twice before (at 12:43 and 14:21)
   - Current watcher shows: "Previously processed CSV files: 0"
   - File not being reprocessed

4. **Check Watcher Metadata:**
   - watcher_metadata collection: **EMPTY**
   - Database was cleared at 14:38 (after watcher processed files)

### Root Cause

**The Clear Database feature cleared the watcher metadata!**

When the database was cleared:
1. All HTTP records were deleted ✅ (intended)
2. watcher_metadata collection was deleted ✅ (intended, to allow reprocessing)
3. **BUT** the watcher service was still running with internal state
4. Watcher didn't reprocess existing files because it only watches for **new or modified** files
5. After watcher restart, it correctly saw 0 processed files, but still didn't auto-process existing CSV

## Why Watcher Doesn't Auto-Process Existing Files

The watcher service uses the **watchdog** library which only triggers on:
- **NEW** files created in the directory
- **MODIFIED** files (timestamp changes)

It does NOT automatically process existing files on startup. This is by design to prevent reprocessing files on every restart.

## The TestTag1/TestTag2 Mystery

The test data was added by running `test_clear_frontend.py` which created a single record with TestTag1 and TestTag2 for testing purposes. This was the only data left in the database after clearing.

## Solution & Remediation Strategies

### Immediate Solution (Used)

**Manually run CLI to ingest CSV:**
```bash
docker compose run --rm cli --file /data/hex-tech2025-11-01.csv --rules /data/rules.yaml
```

**Result:**
- ✅ 909 records processed
- ✅ 266 records tagged
- ✅ 13 unique tags created
- ✅ UI now displays real data

### Alternative Solutions

#### Option 1: Touch File to Trigger Watcher
```bash
# Update file modification time
touch data/hex-tech2025-11-01.csv
```
**Note:** This should work but may not trigger if watcher has internal debouncing.

#### Option 2: Copy File to Trigger New File Event
```bash
# Make watcher see it as new file
mv data/hex-tech2025-11-01.csv data/hex-tech2025-11-01.csv.bak
cp data/hex-tech2025-11-01.csv.bak data/hex-tech2025-11-01.csv
```

#### Option 3: Restart All Services
```bash
# Stop everything
docker compose down

# Start everything fresh
docker compose up -d

# Then manually ingest
docker compose run --rm cli --file /data/hex-tech2025-11-01.csv --rules /data/rules.yaml
```

## Recommended: Improve Clear Database Feature

The clear database feature should provide guidance on reingesting data. Here are recommendations:

### Enhancement 1: Update Clear Database Message

Modify the success alert to include reingest instructions:

```javascript
alert(
    `Database cleared successfully!\n\n` +
    `Deleted ${data.message}\n\n` +
    `To reingest your CSV data, run:\n` +
    `docker compose run --rm cli --file /data/your-file.csv --rules /data/rules.yaml`
);
```

### Enhancement 2: Add "Reingest Data" Button

Add a button in the UI that triggers the CLI ingestion:
- Button: "Import CSV Files"
- Action: Trigger API endpoint that runs CLI internally
- Or: Show command for user to run manually

### Enhancement 3: Watcher Auto-Scan on Startup

Modify watcher to check for CSV files without metadata on startup:

```python
def check_existing_files():
    """Check for CSV files that should be processed on startup"""
    for csv_file in data_dir.glob('*.csv'):
        # Check if file is in metadata
        if not is_file_processed(csv_file.name):
            # Process it
            _ingest_csv_file(csv_file.name)
```

## Prevention: Best Practices

### Before Clearing Database

1. **Understand what will be deleted:**
   - All HTTP records
   - All enrichment events
   - All watcher metadata
   - Tags will disappear

2. **Know how to restore data:**
   - CSV files are NOT deleted (they're in /data directory)
   - Rules are NOT deleted (rules.yaml remains)
   - You must manually reingest after clearing

3. **Document your CSV files:**
   - Keep track of which CSV you're analyzing
   - Name files with dates/projects for clarity

### After Clearing Database

**Standard workflow:**
```bash
# 1. Clear database via UI or API
curl -X DELETE http://localhost:8000/api/clear-all

# 2. Reingest your CSV
docker compose run --rm cli --file /data/your-file.csv --rules /data/rules.yaml

# 3. Verify in UI
# Open http://localhost:9999/ and check tags
```

## Testing Your Data

### Verify CSV is Properly Loaded

```python
from pymongo import MongoClient

client = MongoClient('mongodb://admin:password123@localhost:27017/')
db = client['http_tagger']

# Check counts
print(f"Total records: {db.records.count_documents({})}")
print(f"Tagged records: {db.records.count_documents({'tags': {'$ne': []}})}")

# Check tags
tags = db.records.distinct('tags')
print(f"Unique tags: {len(tags)}")
print(f"Tags: {tags}")
```

### Verify Rules are Applied

```bash
# Check rules file exists
ls -lh data/rules.yaml

# View rules
cat data/rules.yaml | head -50
```

### Check UI

1. Open http://localhost:9999/
2. Verify tags sidebar shows your actual tags (not TestTag1/TestTag2)
3. Click on tags to verify records load
4. Expand records to verify request/response data

## Files and Services Status

After resolution:

```bash
# Services running
docker compose ps
# Should show: api, frontend, watcher, mongo all running

# Data files present
ls -lh data/
# Should show: hex-tech2025-11-01.csv, rules.yaml

# Database populated
# 910 records total (909 from CSV + 1 test record)
# 13 unique tags
```

## Summary

**Problem:** Database was cleared but watcher didn't automatically reprocess existing CSV files.

**Why:** Watcher only processes new/modified files, not existing files on startup.

**Solution:** Manually run CLI to ingest CSV data.

**Lesson:** After clearing database, you must manually reingest CSV files using the CLI tool.

## Quick Reference Commands

```bash
# Check what's in database
docker exec -it traffic_tagger_mongo mongosh -u admin -p password123 http_tagger --eval "db.records.countDocuments({})"

# List CSV files
ls -lh data/*.csv

# Manually ingest CSV
docker compose run --rm cli --file /data/your-file.csv --rules /data/rules.yaml

# Check watcher logs
docker compose logs watcher --tail 50

# Restart watcher
docker compose restart watcher

# Clear test data
python3 << 'EOF'
from pymongo import MongoClient
client = MongoClient('mongodb://admin:password123@localhost:27017/')
db = client['http_tagger']
# Delete only test records
db.records.delete_many({'tags': {'$in': ['TestTag1', 'TestTag2']}})
print('Test data removed')
EOF
```

## Related Documentation

- `CLEAR_DATABASE_FEATURE.md` - Original clear feature docs
- `CLEAR_DATABASE_FIX.md` - Frontend caching fix
- `WARP.md` - Watcher service documentation
