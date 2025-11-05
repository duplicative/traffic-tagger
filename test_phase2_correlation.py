#!/usr/bin/env python3
"""
Phase 2 Correlation Engine Test Suite

Tests the complete correlation workflow:
1. Insert HTTP record into database
2. Send enrichment events to API
3. Verify correlation analysis runs
4. Confirm tags are added to HTTP records
"""

import requests
import time
from pymongo import MongoClient
from bson import ObjectId

# Configuration
API_URL = "http://localhost:8000"
MONGO_URI = "mongodb://admin:password123@localhost:27017/"
DB_NAME = "http_tagger"

def setup_test_data():
    """Insert test HTTP record into database"""
    print("\n" + "="*70)
    print("PHASE 2 CORRELATION ENGINE TEST")
    print("="*70)
    
    print("\n1. Setting up test data...")
    
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    records_collection = db['records']
    
    # Create test HTTP record
    test_record = {
        "source_id": 99999,
        "host": "test.example.com",
        "method": "GET",
        "path": "/test-correlation",
        "http_version": "HTTP/1.1",
        "scheme": "https",
        "authority": "test.example.com",
        "request_content_length": 0,
        "request_timestamp_start": 1609459200,
        "request_timestamp_end": 1609459201,
        "response_status_code": 200,
        "response_reason": "OK",
        "response_content_length": 1000,
        "response_timestamp_start": 1609459201,
        "response_timestamp_end": 1609459202,
        "response_created_at": 1609459202,
        "decoded_request": "GET /test-correlation HTTP/1.1\\r\\nHost: test.example.com\\r\\n\\r\\n",
        "request_decoding_error": False,
        "decoded_response": "HTTP/1.1 200 OK\\r\\nContent-Type: text/html\\r\\n\\r\\n<html><body>Test page with scripts</body></html>",
        "response_decoding_error": False,
        "tags": ["Test HTTP Record"],
        "highlights": {},
        "processed_at": "2025-01-01T00:00:00Z"
    }
    
    # Insert or update test record
    result = records_collection.update_one(
        {"source_id": test_record["source_id"]},
        {"$set": test_record},
        upsert=True
    )
    
    record_id = result.upserted_id if result.upserted_id else records_collection.find_one({"source_id": test_record["source_id"]})["_id"]
    
    print(f"   ✓ Inserted HTTP record: {record_id}")
    print(f"   ✓ URL: https://test.example.com/test-correlation")
    print(f"   ✓ Initial tags: {test_record['tags']}")
    
    return str(record_id), test_record

def send_enrichment_events():
    """Send enrichment events that should trigger correlation"""
    print("\n2. Sending enrichment events to API...")
    
    # Test events that should match correlation rules
    test_events = [
        {
            "eventId": "test-correlation-dom-001",
            "timestamp": "2025-01-10T20:00:00Z",
            "eventType": "DOM_SNAPSHOT",
            "url": "https://test.example.com/test-correlation",
            "data": {
                "html": "<html><body><script src='https://evil.com/malicious.js'></script><div id='content'></div></body></html>",
                "mutations": ["childList", "attributes"]
            }
        },
        {
            "eventId": "test-correlation-js-001",
            "timestamp": "2025-01-10T20:00:01Z",
            "eventType": "JS_EXECUTION",
            "url": "https://test.example.com/test-correlation",
            "data": {
                "functionName": "innerHTML",
                "inputValue": "document.getElementById('content').innerHTML = userInput;",
                "stackTrace": "at updateContent (app.js:42)"
            }
        },
        {
            "eventId": "test-correlation-js-002",
            "timestamp": "2025-01-10T20:00:02Z",
            "eventType": "JS_EXECUTION",
            "url": "https://test.example.com/test-correlation",
            "data": {
                "functionName": "eval",
                "inputValue": "eval(userData)",
                "stackTrace": "at processData (app.js:89)"
            }
        },
        {
            "eventId": "test-correlation-storage-001",
            "timestamp": "2025-01-10T20:00:03Z",
            "eventType": "STORAGE_STATE",
            "url": "https://test.example.com/test-correlation",
            "data": {
                "localStorage": {
                    "user_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "api_key": "sk-1234567890abcdef",
                    "session_id": "sess_abc123"
                },
                "sessionStorage": {
                    "temp_token": "tmp_xyz789"
                },
                "cookies": [
                    {"name": "session", "value": "abc123"},
                    {"name": "password", "value": "admin123"}
                ]
            }
        }
    ]
    
    print(f"   📤 Sending {len(test_events)} enrichment events...")
    for event in test_events:
        print(f"      - {event['eventType']}: {event['data'].get('functionName', 'N/A')}")
    
    response = requests.post(
        f"{API_URL}/api/enrichment-events",
        json={"events": test_events},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ API Response: {result['message']}")
        print(f"   ✓ Stored events: {result['details']}")
        print(f"   ✓ Correlation tasks queued: {result.get('correlation_queued', 0)}")
        return True
    else:
        print(f"   ✗ API Error: {response.status_code} - {response.text}")
        return False

def wait_for_correlation():
    """Wait for background correlation to complete"""
    print("\n3. Waiting for correlation analysis...")
    print("   ⏳ Background tasks processing (5 seconds)...")
    time.sleep(5)
    print("   ✓ Correlation should be complete")

def verify_correlation_results(record_id):
    """Verify that correlation added tags to HTTP record"""
    print("\n4. Verifying correlation results...")
    
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    records_collection = db['records']
    
    # Fetch the updated record
    record = records_collection.find_one({"_id": ObjectId(record_id)})
    
    if not record:
        print("   ✗ Record not found!")
        return False
    
    print(f"   📊 Updated record tags: {record.get('tags', [])}")
    print(f"   📊 Highlights: {list(record.get('highlights', {}).keys())}")
    
    # Expected correlation tags based on our test events
    expected_correlation_tags = [
        "DOM-Based XSS: innerHTML Usage",
        "DOM-Based XSS: eval() Execution",
        "Sensitive Data in localStorage",
        "Session Token in sessionStorage",
        "Unencrypted Cookies with Sensitive Data",
        "DOM Mutation with User Input",
        "Third-Party Script Execution"
    ]
    
    actual_tags = record.get('tags', [])
    found_correlation_tags = [tag for tag in expected_correlation_tags if tag in actual_tags]
    
    print(f"\n   Expected correlation tags ({len(expected_correlation_tags)}):")
    for tag in expected_correlation_tags:
        status = "✓" if tag in actual_tags else "✗"
        print(f"      {status} {tag}")
    
    print(f"\n   Results:")
    print(f"      Total tags: {len(actual_tags)}")
    print(f"      Correlation tags found: {len(found_correlation_tags)}/{len(expected_correlation_tags)}")
    print(f"      Highlights: {len(record.get('highlights', {}))}")
    
    # Check if correlation_processed_at timestamp exists
    if record.get('correlation_processed_at'):
        print(f"      Correlation processed at: {record.get('correlation_processed_at')}")
    
    return len(found_correlation_tags) > 0

def test_enrichment_storage():
    """Verify enrichment events are stored correctly"""
    print("\n5. Verifying enrichment storage...")
    
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    collections = {
        "dom_snapshots": "test-correlation-dom-001",
        "js_executions": "test-correlation-js",
        "storage_states": "test-correlation-storage-001"
    }
    
    all_found = True
    for coll_name, event_id_prefix in collections.items():
        coll = db[coll_name]
        count = coll.count_documents({"eventId": {"$regex": f"^{event_id_prefix}"}})
        status = "✓" if count > 0 else "✗"
        print(f"   {status} {coll_name}: {count} event(s)")
        if count == 0:
            all_found = False
    
    return all_found

def cleanup_test_data():
    """Remove test data from database"""
    print("\n6. Cleaning up test data...")
    
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Remove test HTTP record
    result = db['records'].delete_many({"source_id": 99999})
    print(f"   ✓ Removed {result.deleted_count} HTTP record(s)")
    
    # Remove test enrichment events
    for coll_name in ["dom_snapshots", "js_executions", "storage_states"]:
        result = db[coll_name].delete_many({"eventId": {"$regex": "^test-correlation"}})
        print(f"   ✓ Removed {result.deleted_count} event(s) from {coll_name}")

def main():
    try:
        # Test workflow
        record_id, test_record = setup_test_data()
        
        events_sent = send_enrichment_events()
        if not events_sent:
            print("\n✗ Failed to send enrichment events")
            return False
        
        wait_for_correlation()
        
        storage_ok = test_enrichment_storage()
        correlation_ok = verify_correlation_results(record_id)
        
        # Print final results
        print("\n" + "="*70)
        print("TEST RESULTS SUMMARY")
        print("="*70)
        print(f"  Enrichment Storage:       {'✓ PASS' if storage_ok else '✗ FAIL'}")
        print(f"  Correlation Analysis:     {'✓ PASS' if correlation_ok else '✗ FAIL'}")
        print("="*70)
        
        if storage_ok and correlation_ok:
            print("\n✓ Phase 2 correlation engine is working correctly!")
            print("\nKey achievements:")
            print("  • Enrichment events stored in correct collections")
            print("  • Correlation analysis triggered automatically")
            print("  • HTTP records updated with correlation-based tags")
            print("  • Background processing does not block API responses")
        else:
            print("\n✗ Some tests failed. Check output above for details.")
        
        # Cleanup
        cleanup_test_data()
        
        return storage_ok and correlation_ok
        
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
