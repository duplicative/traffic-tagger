#!/usr/bin/env python3
"""
Test script for Phase 1 sidecar integration.
Simulates sidecar-extension sending enrichment events to traffic-tagger API.
"""
import requests
import json
from datetime import datetime
import uuid

API_URL = "http://localhost:8000/api/enrichment-events"

def generate_test_events():
    """Generate test enrichment events"""
    test_url = "https://example.com/test-page"
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    events = [
        # DOM_SNAPSHOT event
        {
            "eventId": str(uuid.uuid4()),
            "timestamp": timestamp,
            "eventType": "DOM_SNAPSHOT",
            "url": test_url,
            "data": {
                "html": "<div id='test'>Example DOM content with potential XSS vector</div>",
                "mutations": [
                    "innerHTML set on #test",
                    "appendChild on body"
                ]
            }
        },
        # JS_EXECUTION event
        {
            "eventId": str(uuid.uuid4()),
            "timestamp": timestamp,
            "eventType": "JS_EXECUTION",
            "url": test_url,
            "data": {
                "functionName": "eval",
                "inputValue": "document.write('<script>alert(1)</script>')",
                "stackTrace": "at eval (example.com/test.js:42:10)\nat processUserInput (example.com/test.js:15:5)"
            }
        },
        # STORAGE_STATE event
        {
            "eventId": str(uuid.uuid4()),
            "timestamp": timestamp,
            "eventType": "STORAGE_STATE",
            "url": test_url,
            "data": {
                "localStorage": {
                    "authToken": "Bearer_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
                    "userPrefs": "{\"theme\":\"dark\"}"
                },
                "sessionStorage": {
                    "sessionId": "abc123xyz"
                },
                "cookies": [
                    {"name": "PHPSESSID", "value": "s3cr3t_t0k3n"},
                    {"name": "auth", "value": "admin:password"}
                ]
            }
        }
    ]
    
    return events

def test_send_events():
    """Send test events to API"""
    print("=" * 60)
    print("Phase 1 Integration Test: Sidecar → Traffic Tagger API")
    print("=" * 60)
    
    events = generate_test_events()
    
    print(f"\n📤 Sending {len(events)} test events to API...")
    print(f"   URL: {API_URL}")
    
    for event in events:
        print(f"   - {event['eventType']}: {event['url']}")
    
    try:
        response = requests.post(
            API_URL,
            json={"events": events},
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.ok:
            result = response.json()
            print("✅ Success!")
            print(f"   Message: {result.get('message')}")
            print(f"   Details: {json.dumps(result.get('details'), indent=2)}")
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Is the API service running?")
        print("   Try: docker compose up -d")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def verify_storage():
    """Verify events were stored in MongoDB"""
    print("\n" + "=" * 60)
    print("Verifying MongoDB Storage")
    print("=" * 60)
    
    try:
        from pymongo import MongoClient
        
        client = MongoClient("mongodb://admin:password123@localhost:27017/")
        db = client["http_tagger"]
        
        collections = {
            "dom_snapshots": db.dom_snapshots,
            "js_executions": db.js_executions,
            "storage_states": db.storage_states
        }
        
        print("\n📊 Collection Statistics:")
        for name, collection in collections.items():
            count = collection.count_documents({})
            print(f"   {name}: {count} documents")
            
            if count > 0:
                # Show latest document
                latest = collection.find_one(
                    sort=[("received_at", -1)]
                )
                if latest:
                    print(f"      Latest: {latest.get('eventType')} - {latest.get('url')}")
        
        print("\n✅ Storage verification complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying storage: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_send_events()
    
    if success:
        verify_storage()
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
