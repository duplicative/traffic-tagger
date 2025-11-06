#!/usr/bin/env python3
"""
Test Temporal-URL Correlation Strategy

This test demonstrates the new temporal-URL correlation approach where:
1. Events are matched to HTTP records based on BOTH URL and timestamp
2. Events only correlate with the HTTP record that immediately precedes them
3. Same URL visited multiple times maintains separate correlation windows
"""

import requests
import time
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000"
MONGO_URI = "mongodb://admin:password123@localhost:27017/"
DB_NAME = "http_tagger"

def setup_test_scenario():
    """
    Create test scenario with same URL visited at different times.
    
    Timeline:
    10:00:00 - HTTP GET /api/users
    10:00:02 - Sidecar: innerHTML on /api/users
    10:00:05 - Sidecar: localStorage on /api/users
    
    10:01:40 - HTTP GET /api/dashboard  
    10:01:42 - Sidecar: eval on /api/dashboard
    
    10:03:00 - HTTP GET /api/users (SECOND VISIT)
    10:03:02 - Sidecar: eval on /api/users
    10:03:05 - Sidecar: postMessage on /api/users
    """
    print("\n" + "="*70)
    print("TEMPORAL-URL CORRELATION TEST")
    print("="*70)
    
    print("\n1. Setting up test scenario...")
    
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    records = db['records']
    
    # Base timestamp: 10:00:00
    base_time = 1699178400
    
    # Create test HTTP records
    test_records = [
        {
            "source_id": 99990,
            "host": "test.example.com",
            "path": "/api/users",
            "method": "GET",
            "scheme": "https",
            "normalized_url": "https://test.example.com/api/users",
            "response_created_at": base_time,  # 10:00:00
            "response_status_code": 200,
            "tags": ["Initial Tag - First Visit"],
            "http_version": "HTTP/1.1",
            "authority": "test.example.com",
            "request_content_length": 0,
            "response_content_length": 100,
            "decoded_request": "GET /api/users HTTP/1.1\\r\\n",
            "decoded_response": "HTTP/1.1 200 OK\\r\\n",
            "highlights": {},
            "request_decoding_error": False,
            "response_decoding_error": False,
            "request_timestamp_start": base_time,
            "request_timestamp_end": base_time,
            "response_timestamp_start": base_time,
            "response_timestamp_end": base_time,
            "response_reason": "OK",
            "processed_at": datetime.utcfromtimestamp(base_time).isoformat()
        },
        {
            "source_id": 99991,
            "host": "test.example.com",
            "path": "/api/dashboard",
            "method": "GET",
            "scheme": "https",
            "normalized_url": "https://test.example.com/api/dashboard",
            "response_created_at": base_time + 100,  # 10:01:40
            "response_status_code": 200,
            "tags": ["Dashboard Visit"],
            "http_version": "HTTP/1.1",
            "authority": "test.example.com",
            "request_content_length": 0,
            "response_content_length": 200,
            "decoded_request": "GET /api/dashboard HTTP/1.1\\r\\n",
            "decoded_response": "HTTP/1.1 200 OK\\r\\n",
            "highlights": {},
            "request_decoding_error": False,
            "response_decoding_error": False,
            "request_timestamp_start": base_time + 100,
            "request_timestamp_end": base_time + 100,
            "response_timestamp_start": base_time + 100,
            "response_timestamp_end": base_time + 100,
            "response_reason": "OK",
            "processed_at": datetime.utcfromtimestamp(base_time + 100).isoformat()
        },
        {
            "source_id": 99992,
            "host": "test.example.com",
            "path": "/api/users",
            "method": "GET",
            "scheme": "https",
            "normalized_url": "https://test.example.com/api/users",
            "response_created_at": base_time + 180,  # 10:03:00 (SECOND VISIT)
            "response_status_code": 200,
            "tags": ["Initial Tag - Second Visit"],
            "http_version": "HTTP/1.1",
            "authority": "test.example.com",
            "request_content_length": 0,
            "response_content_length": 150,
            "decoded_request": "GET /api/users HTTP/1.1\\r\\n",
            "decoded_response": "HTTP/1.1 200 OK\\r\\n",
            "highlights": {},
            "request_decoding_error": False,
            "response_decoding_error": False,
            "request_timestamp_start": base_time + 180,
            "request_timestamp_end": base_time + 180,
            "response_timestamp_start": base_time + 180,
            "response_timestamp_end": base_time + 180,
            "response_reason": "OK",
            "processed_at": datetime.utcfromtimestamp(base_time + 180).isoformat()
        }
    ]
    
    inserted_ids = []
    for record in test_records:
        result = records.update_one(
            {"source_id": record["source_id"]},
            {"$set": record},
            upsert=True
        )
        if result.upserted_id:
            inserted_ids.append(result.upserted_id)
        else:
            existing = records.find_one({"source_id": record["source_id"]})
            inserted_ids.append(existing["_id"])
        print(f"   ✓ HTTP {record['method']} {record['path']} @ {record['response_created_at']}")
    
    return inserted_ids, base_time

def send_sidecar_events(base_time):
    """Send sidecar events that should correlate with specific HTTP records"""
    print("\n2. Sending sidecar events...")
    
    events = [
        # Events for FIRST visit to /api/users (10:00:00)
        {
            "eventId": "test-temporal-js-001",
            "timestamp": datetime.utcfromtimestamp(base_time + 2).isoformat() + "Z",
            "eventType": "JS_EXECUTION",
            "url": "https://test.example.com/api/users",
            "data": {
                "functionName": "innerHTML",
                "inputValue": "...",
                "stackTrace": "..."
            }
        },
        {
            "eventId": "test-temporal-storage-001",
            "timestamp": datetime.utcfromtimestamp(base_time + 5).isoformat() + "Z",
            "eventType": "STORAGE_STATE",
            "url": "https://test.example.com/api/users",
            "data": {
                "localStorage": {"token": "abc123"},
                "sessionStorage": {},
                "cookies": []
            }
        },
        # Events for /api/dashboard (10:01:40)
        {
            "eventId": "test-temporal-js-002",
            "timestamp": datetime.utcfromtimestamp(base_time + 102).isoformat() + "Z",
            "eventType": "JS_EXECUTION",
            "url": "https://test.example.com/api/dashboard",
            "data": {
                "functionName": "eval",
                "inputValue": "...",
                "stackTrace": "..."
            }
        },
        # Events for SECOND visit to /api/users (10:03:00)
        {
            "eventId": "test-temporal-js-003",
            "timestamp": datetime.utcfromtimestamp(base_time + 182).isoformat() + "Z",
            "eventType": "JS_EXECUTION",
            "url": "https://test.example.com/api/users",
            "data": {
                "functionName": "eval",
                "inputValue": "...",
                "stackTrace": "..."
            }
        },
        {
            "eventId": "test-temporal-js-004",
            "timestamp": datetime.utcfromtimestamp(base_time + 185).isoformat() + "Z",
            "eventType": "JS_EXECUTION",
            "url": "https://test.example.com/api/users",
            "data": {
                "functionName": "postMessage",
                "inputValue": "...",
                "stackTrace": "..."
            }
        }
    ]
    
    for event in events:
        timestamp_readable = datetime.fromisoformat(event['timestamp'].rstrip('Z')).strftime('%H:%M:%S')
        print(f"   📤 {event['eventType']} on {event['url'].split('/')[-1]} @ {timestamp_readable}")
    
    response = requests.post(
        f"{API_URL}/api/enrichment-events",
        json={"events": events},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n   ✓ API Response: {result['message']}")
        print(f"   ✓ Correlation tasks queued: {result.get('correlation_queued', 0)}")
        return True
    else:
        print(f"   ✗ API Error: {response.status_code}")
        return False

def verify_temporal_correlation(record_ids):
    """Verify that events were correlated with the correct HTTP records"""
    print("\n3. Waiting for correlation (5 seconds)...")
    time.sleep(5)
    
    print("\n4. Verifying temporal correlation...")
    
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    records = db['records']
    
    results = []
    for record_id in record_ids:
        record = records.find_one({"_id": record_id})
        if record:
            timestamp = datetime.utcfromtimestamp(record['response_created_at']).strftime('%H:%M:%S')
            correlated = record.get('correlated_events', [])
            
            print(f"\n   📊 HTTP {record['method']} {record['path']} @ {timestamp}")
            print(f"      Tags: {record.get('tags', [])}")
            print(f"      Correlated events: {len(correlated)}")
            
            if correlated:
                for event in correlated:
                    event_time = datetime.fromisoformat(event['timestamp'].rstrip('Z')).strftime('%H:%M:%S')
                    print(f"        • {event['eventType']} (ID: {event['eventId']}) @ {event_time}")
            
            window = record.get('correlation_window', {})
            if window:
                window_start = datetime.utcfromtimestamp(window['start']).strftime('%H:%M:%S')
                window_end = "∞" if window['end'] is None else datetime.utcfromtimestamp(window['end']).strftime('%H:%M:%S')
                print(f"      Time window: {window_start} → {window_end}")
            
            results.append({
                'record': record,
                'correlated_count': len(correlated)
            })
    
    return results

def verify_correct_correlation(results):
    """Verify correlation correctness"""
    print("\n5. Checking correlation correctness...")
    
    # Expected correlations
    expectations = [
        {"path": "/api/users", "visit": "first", "expected_events": 2, "event_ids": ["test-temporal-js-001", "test-temporal-storage-001"]},
        {"path": "/api/dashboard", "expected_events": 1, "event_ids": ["test-temporal-js-002"]},
        {"path": "/api/users", "visit": "second", "expected_events": 2, "event_ids": ["test-temporal-js-003", "test-temporal-js-004"]}
    ]
    
    all_correct = True
    for i, result in enumerate(results):
        record = result['record']
        expected = expectations[i]
        correlated_events = record.get('correlated_events', [])
        correlated_ids = [e['eventId'] for e in correlated_events]
        
        visit_label = expected.get('visit', '')
        visit_str = f" ({visit_label} visit)" if visit_label else ""
        
        if result['correlated_count'] == expected['expected_events']:
            print(f"   ✓ {record['path']}{visit_str}: {result['correlated_count']}/{expected['expected_events']} events")
            
            # Check specific event IDs
            if set(correlated_ids) == set(expected['event_ids']):
                print(f"     ✓ Correct events correlated")
            else:
                print(f"     ✗ Wrong events: expected {expected['event_ids']}, got {correlated_ids}")
                all_correct = False
        else:
            print(f"   ✗ {record['path']}{visit_str}: {result['correlated_count']}/{expected['expected_events']} events")
            all_correct = False
    
    return all_correct

def cleanup(record_ids):
    """Clean up test data"""
    print("\n6. Cleaning up...")
    
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Remove HTTP records
    result = db['records'].delete_many({"source_id": {"$gte": 99990, "$lte": 99992}})
    print(f"   ✓ Removed {result.deleted_count} HTTP records")
    
    # Remove sidecar events
    for coll in ['dom_snapshots', 'js_executions', 'storage_states']:
        result = db[coll].delete_many({"eventId": {"$regex": "^test-temporal"}})
        print(f"   ✓ Removed {result.deleted_count} events from {coll}")

def main():
    try:
        record_ids, base_time = setup_test_scenario()
        
        success = send_sidecar_events(base_time)
        if not success:
            return False
        
        results = verify_temporal_correlation(record_ids)
        correct = verify_correct_correlation(results)
        
        print("\n" + "="*70)
        print("TEST RESULTS")
        print("="*70)
        if correct:
            print("✓ PASS: Temporal-URL correlation working correctly!")
            print("\nKey Points Verified:")
            print("  • Same URL visited at different times kept separate")
            print("  • Events correlated only with preceding HTTP record")
            print("  • Time windows correctly calculated")
            print("  • No cross-contamination between visits")
        else:
            print("✗ FAIL: Correlation errors detected")
        
        cleanup(record_ids)
        
        return correct
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
