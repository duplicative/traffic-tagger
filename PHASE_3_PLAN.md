# Phase 3: Correlation Execution and End-to-End Integration

## Overview
Phase 3 completes the temporal-URL correlation implementation by executing correlation on existing data and validating the complete workflow from sidecar events → correlation → timeline visualization.

## Goals
1. Execute correlation on all 909 HTTP records with 602 enrichment events
2. Validate correlation results and populate `correlated_events` field
3. Test end-to-end workflow: enrichment ingestion → correlation → timeline display
4. Create automated correlation execution mechanism
5. Document correlation workflow and usage

## Implementation Tasks

### Task 1: Create Correlation Execution Script
Create a Python script that:
- Connects to MongoDB
- Loads all HTTP records
- Loads all enrichment events from all three collections
- Executes temporal-URL correlation algorithm
- Updates HTTP records with correlated events
- Provides detailed statistics and progress feedback

**Deliverable**: `run_correlation.py`

### Task 2: Add Correlation to API
Add an API endpoint to trigger correlation on-demand:
- `POST /api/run-correlation` - Executes correlation and returns stats
- Supports running correlation in background
- Returns correlation status and progress

**Deliverable**: Updated `api/main.py`

### Task 3: Integration Testing
Create comprehensive integration test that validates:
- Enrichment events are properly ingested
- Correlation correctly matches events to HTTP records
- Time windows are calculated correctly
- No cross-contamination between same-URL visits
- Timeline API returns correlated data
- Frontend displays correlated events correctly

**Deliverable**: `test_phase3_integration.py`

### Task 4: Watcher Integration
Update the watcher service to automatically run correlation when:
- New CSV files are ingested (new HTTP records added)
- New enrichment events are received
- Option to run on schedule (e.g., every 5 minutes)

**Deliverable**: Updated `watcher/main.py`

### Task 5: Documentation
Document the complete correlation workflow:
- How correlation works (temporal-URL strategy)
- When to run correlation
- How to interpret correlation results
- Troubleshooting correlation issues

**Deliverable**: `CORRELATION_GUIDE.md`

## Success Criteria
- ✅ Correlation executes on 909 HTTP records successfully
- ✅ Correlation rate > 0% (events matched to records)
- ✅ Timeline UI displays correlated events with time deltas
- ✅ No cross-contamination between same-URL visits
- ✅ Integration tests pass
- ✅ Documentation complete

## Expected Outcomes
- HTTP records will have populated `correlated_events` arrays
- Timeline UI will display nested events under HTTP records
- Users can trace client-side behavior triggered by API calls
- System automatically maintains correlation as new data arrives
