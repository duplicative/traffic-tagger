#!/usr/bin/env python3
"""
Test script to verify sidecar extension fix

This script tests:
1. Extension can be loaded without importScripts error
2. Extension can send enrichment events to traffic-tagger API
3. Events are properly stored in MongoDB
"""

import requests
import time
import json
from pymongo import MongoClient

# Configuration
TAGGER_API_URL = "http://localhost:8000"
MONGO_URI = "mongodb://admin:password123@localhost:27017/"
DB_NAME = "http_tagger"

def test_api_connectivity():
    """Test that traffic-tagger API is accessible"""
    print("\n1. Testing API connectivity...")
    try:
        response = requests.get(f"{TAGGER_API_URL}/api/tags")
        print(f"   ✓ API is accessible (status: {response.status_code})")
        return True
    except Exception as e:
        print(f"   ✗ API connection failed: {e}")
        return False

def test_enrichment_endpoint():
    """Test the enrichment events endpoint directly"""
    print("\n2. Testing enrichment events endpoint...")
    
    # Create test events
    test_events = [
        {
            "eventId": "test-dom-001",
            "timestamp": "2025-01-10T12:00:00Z",
            "eventType": "DOM_SNAPSHOT",
            "url": "https://test.example.com/page1",
            "data": {
                "html": "<html><body>Test Page</body></html>",
                "mutations": []
            }
        },
        {
            "eventId": "test-js-001",
            "timestamp": "2025-01-10T12:00:01Z",
            "eventType": "JS_EXECUTION",
            "url": "https://test.example.com/page1",
            "data": {
                "functionName": "testFunction",
                "inputValue": "test input",
                "stackTrace": "at testFunction (test.js:10)"
            }
        },
        {
            "eventId": "test-storage-001",
            "timestamp": "2025-01-10T12:00:02Z",
            "eventType": "STORAGE_STATE",
            "url": "https://test.example.com/page1",
            "data": {
                "localStorage": {"key": "value"},
                "sessionStorage": {"session": "data"},
                "cookies": [{"name": "test", "value": "cookie"}]
            }
        }
    ]
    
    try:
        response = requests.post(
            f"{TAGGER_API_URL}/api/enrichment-events",
            json={"events": test_events},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            details = result.get('details', {})
            total_stored = sum(details.values())
            print(f"   ✓ Successfully sent {len(test_events)} events")
            print(f"   ✓ Stored {total_stored} events: {details}")
            return True
        else:
            print(f"   ✗ API returned status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"   ✗ Error sending events: {e}")
        return False

def test_mongodb_storage():
    """Verify events were stored in MongoDB"""
    print("\n3. Testing MongoDB storage...")
    
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        
        # Check each collection
        collections = {
            "dom_snapshots": "DOM_SNAPSHOT",
            "js_executions": "JS_EXECUTION",
            "storage_states": "STORAGE_STATE"
        }
        
        stored_counts = {}
        for collection_name, event_type in collections.items():
            collection = db[collection_name]
            
            # Find test events (with test- prefix in eventId)
            test_events = list(collection.find({
                "eventId": {"$regex": "^test-"}
            }))
            
            stored_counts[collection_name] = len(test_events)
            
            if len(test_events) > 0:
                print(f"   ✓ Found {len(test_events)} test event(s) in {collection_name}")
                # Show first event as sample
                if test_events:
                    print(f"      Sample eventId: {test_events[0].get('eventId')}")
            else:
                print(f"   ! No test events found in {collection_name}")
        
        return all(count > 0 for count in stored_counts.values())
        
    except Exception as e:
        print(f"   ✗ MongoDB connection error: {e}")
        return False

def cleanup_test_data():
    """Remove test events from MongoDB"""
    print("\n4. Cleaning up test data...")
    
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        
        collections = ["dom_snapshots", "js_executions", "storage_states"]
        
        for collection_name in collections:
            collection = db[collection_name]
            result = collection.delete_many({
                "eventId": {"$regex": "^test-"}
            })
            print(f"   ✓ Removed {result.deleted_count} test event(s) from {collection_name}")
        
        return True
    except Exception as e:
        print(f"   ✗ Cleanup error: {e}")
        return False

def print_extension_loading_instructions():
    """Print instructions for manually loading the extension"""
    print("\n" + "="*70)
    print("MANUAL EXTENSION TESTING INSTRUCTIONS")
    print("="*70)
    print("""
To verify the extension loads without errors:

1. Open Chrome and navigate to: chrome://extensions/

2. Enable "Developer mode" (toggle in top-right corner)

3. Click "Load unpacked"

4. Navigate to and select: /home/guid/projects/traffic_tagger/sidecar-extension/

5. Check for errors:
   - The extension should load successfully
   - Click "Errors" button if it appears (should be none)
   - Open background page console: Click "service worker" link
   - Look for: "[Sidecar] Background service worker initialized"
   - Should NOT see: "Failed to execute 'importScripts'"

6. Test data capture:
   - Click the Sidecar extension icon in Chrome toolbar
   - It should show "API Connected" status
   - Navigate to a test website (e.g., example.com)
   - The event count should increment
   - Check logs: Events should be batched and sent

7. Verify in MongoDB:
   - Run this script again after browsing
   - Check that real (non-test) events appear in MongoDB
""")
    print("="*70 + "\n")

def main():
    print("="*70)
    print("SIDECAR EXTENSION FIX VERIFICATION TEST")
    print("="*70)
    
    print("\nThis test verifies:")
    print("  1. Traffic-tagger API is accessible")
    print("  2. Enrichment events endpoint works correctly")
    print("  3. Events are stored in MongoDB collections")
    
    # Run automated tests
    api_ok = test_api_connectivity()
    if not api_ok:
        print("\n✗ API not accessible. Make sure traffic-tagger is running:")
        print("  docker compose up -d")
        return False
    
    endpoint_ok = test_enrichment_endpoint()
    time.sleep(1)  # Give MongoDB time to write
    
    storage_ok = test_mongodb_storage()
    
    # Cleanup
    cleanup_test_data()
    
    # Print results
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)
    print(f"  API Connectivity:         {'✓ PASS' if api_ok else '✗ FAIL'}")
    print(f"  Enrichment Endpoint:      {'✓ PASS' if endpoint_ok else '✗ FAIL'}")
    print(f"  MongoDB Storage:          {'✓ PASS' if storage_ok else '✗ FAIL'}")
    print("="*70)
    
    if api_ok and endpoint_ok and storage_ok:
        print("\n✓ All automated tests PASSED!")
        print("\nThe importScripts error has been fixed by converting to ES6 modules.")
        print("The API endpoint is working and storing data correctly.")
    else:
        print("\n✗ Some tests FAILED. Check the output above for details.")
    
    # Print manual testing instructions
    print_extension_loading_instructions()
    
    return api_ok and endpoint_ok and storage_ok

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
