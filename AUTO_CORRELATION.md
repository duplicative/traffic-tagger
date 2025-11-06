# Automatic Correlation

The traffic-tagger system now includes **automatic correlation** that runs without user intervention.

## How It Works

The watcher service automatically correlates sidecar enrichment events with HTTP records in three scenarios:

### 1. After CSV Ingestion 📥
When new CSV files are added to the `data/` directory:
- Watcher detects the new file
- Ingests HTTP records into MongoDB
- **Automatically triggers correlation** on the new data

### 2. Periodic Schedule ⏰
Correlation runs automatically every **5 minutes**:
- Checks if enrichment events exist
- Correlates all HTTP records with available events
- Updates correlation rate in real-time

### 3. Manual Execution 🖱️
You can still manually trigger correlation anytime:
```bash
python3 run_correlation.py
```

## Configuration

### Change Correlation Interval

Edit `watcher/main.py` line 55:
```python
self.correlation_interval = 300  # 300 seconds = 5 minutes
```

Options:
- `60` = Every 1 minute (high frequency)
- `300` = Every 5 minutes (default, balanced)
- `600` = Every 10 minutes (low frequency)
- `1800` = Every 30 minutes (very low frequency)

### Disable Automatic Correlation

If you want to disable automatic correlation:

**Option 1: Disable periodic correlation**
Comment out in `watcher/main.py` around line 492:
```python
# event_handler.check_periodic_correlation()
```

**Option 2: Disable post-ingestion correlation**
Comment out in `watcher/main.py` around line 355:
```python
# if records_inserted > 0:
#     logger.info("New records added, triggering correlation...")
#     self._run_correlation()
```

## Monitoring

### Check Watcher Logs
```bash
docker compose logs -f watcher
```

You'll see correlation activity:
```
============================================================
CORRELATION INITIATED
============================================================
Found 247 unique URLs to correlate
Found 602 enrichment events
Progress: 50/247 URLs processed
Progress: 100/247 URLs processed
...
============================================================
CORRELATION COMPLETE
- URLs Processed: 247
- Records Correlated: 156
- Errors: 0
- Overall Correlation Rate: 17.2%
============================================================
```

### Check Correlation Status

Via API:
```bash
curl http://localhost:8000/api/correlation-stats
```

Via Timeline UI:
1. Open http://localhost:9999/
2. Click "Correlation Timeline" tab
3. Statistics header shows correlation rate

## Behavior Details

### Triggers

✅ **Automatic correlation runs when:**
- New CSV file is ingested AND records are added
- 5 minutes have elapsed since last correlation
- Enrichment events exist in the database

❌ **Correlation is skipped when:**
- No enrichment events exist
- CSV ingestion added 0 records (duplicates)
- Correlation ran less than 5 minutes ago

### Performance

- **Small datasets** (< 1,000 records): < 1 second
- **Medium datasets** (1,000-10,000 records): 1-10 seconds
- **Large datasets** (10,000+ records): 10-60 seconds

Correlation is efficient because:
- Uses MongoDB indexes for fast temporal queries
- Processes URLs in batches
- Only correlates records with matching URLs

### Data Safety

Correlation is **non-destructive**:
- ✅ Existing tags are preserved
- ✅ Adds `correlated_events` field
- ✅ Adds `correlation_window` field
- ✅ Idempotent (safe to run multiple times)
- ✅ No data is deleted

## Troubleshooting

### Correlation Not Running

**Check watcher is running:**
```bash
docker compose ps watcher
```

Should show "Up" status.

**Check watcher logs:**
```bash
docker compose logs watcher --tail=50
```

Look for "CORRELATION INITIATED" messages.

**Restart watcher:**
```bash
docker compose restart watcher
```

### Correlation Rate is 0%

**Possible causes:**
1. No enrichment events captured yet
   - Install sidecar extension
   - Browse target application
   - Events should flow to MongoDB

2. URL mismatch between HTTP records and events
   - HTTP records use `normalized_url`
   - Events use `url` field
   - Both must match exactly

3. Timestamp issues
   - HTTP records need `response_created_at`
   - Events need `timestamp` in ISO 8601 format
   - Check data integrity

**Verify enrichment events exist:**
```bash
docker compose exec database mongo http_tagger --eval "
  db.dom_snapshots.countDocuments();
  db.js_executions.countDocuments();
  db.storage_states.countDocuments();
"
```

### High Error Count

Check watcher logs for specific errors:
```bash
docker compose logs watcher | grep -i error
```

Common issues:
- Missing `normalized_url` field: Run migration script
- Malformed timestamps: Check data format
- Database connection issues: Verify MongoDB is accessible

## Best Practices

### For Development
- Use **1-minute interval** for rapid testing
- Monitor watcher logs actively
- Clear database between test runs

### For Production
- Use **5-minute interval** (default) for balance
- Set up log aggregation (ELK, Splunk)
- Monitor correlation rate metrics
- Scale horizontally if needed

### For Low-Volume
- Use **10-30 minute interval** to reduce overhead
- Manual correlation may be sufficient
- Consider disabling periodic correlation

## Architecture

```
Sidecar Extension
       ↓
  Enrichment Events
       ↓
  POST /api/enrichment-events
       ↓
    MongoDB (dom_snapshots, js_executions, storage_states)
       ↓
  Watcher Service (every 5 min)
       ↓
  run_correlation_for_url()
       ↓
  Updated HTTP Records (with correlated_events)
       ↓
  Timeline UI Display
```

## Summary

| Method | When | User Action |
|--------|------|-------------|
| **Post-Ingestion** | After CSV ingested | Drop CSV in data/ |
| **Periodic** | Every 5 minutes | None (automatic) |
| **Manual** | On demand | Run `python3 run_correlation.py` |

**Default behavior:** Correlation runs automatically every 5 minutes and after each CSV ingestion. No user intervention required! 🎉
