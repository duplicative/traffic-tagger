#!/usr/bin/env python3
"""
Test clear database functionality with actual data.
This adds test data, then shows how to verify clearing works.
"""
import requests
from pymongo import MongoClient
import uuid
from datetime import datetime

API_URL = "http://localhost:8000"
MONGO_URI = "mongodb://admin:password123@localhost:27017/"

def add_test_data():
    """Add test data to database"""
    print("=" * 60)
    print("Adding Test Data")
    print("=" * 60)
    
    client = MongoClient(MONGO_URI)
    db = client["http_tagger"]
    
    # Add test HTTP record
    test_record = {
        "source_id": 1,
        "host": "example.com",
        "method": "GET",
        "path": "/test",
        "response_status_code": 200,
        "decoded_request": "GET /test HTTP/1.1\nHost: example.com",
        "decoded_response": "HTTP/1.1 200 OK\nContent-Type: text/html",
        "tags": ["TestTag1", "TestTag2"],
        "highlights": {},
        "processed_at": datetime.utcnow().isoformat()
    }
    
    db.records.insert_one(test_record)
    print("✅ Added 1 test HTTP record")
    
    # Add test enrichment events
    test_dom = {
        "eventId": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "eventType": "DOM_SNAPSHOT",
        "url": "https://example.com/test",
        "data": {"html": "<div>test</div>", "mutations": []},
        "received_at": datetime.utcnow().isoformat()
    }
    db.dom_snapshots.insert_one(test_dom)
    print("✅ Added 1 test DOM snapshot")
    
    client.close()
    print("\n✅ Test data added successfully!")
    
def check_database():
    """Check database state"""
    client = MongoClient(MONGO_URI)
    db = client["http_tagger"]
    
    counts = {
        "records": db.records.count_documents({}),
        "dom_snapshots": db.dom_snapshots.count_documents({}),
        "js_executions": db.js_executions.count_documents({}),
        "storage_states": db.storage_states.count_documents({})
    }
    
    total = sum(counts.values())
    
    print("\n📊 Database State:")
    for collection, count in counts.items():
        print(f"   {collection}: {count}")
    print(f"   Total: {total}")
    
    client.close()
    return total

def verify_tags_endpoint():
    """Check what tags API returns"""
    print("\n🔍 Checking /api/tags endpoint:")
    try:
        response = requests.get(f"{API_URL}/api/tags")
        if response.ok:
            data = response.json()
            tags = data.get('tags', [])
            print(f"   API returned {len(tags)} tags")
            for tag in tags:
                print(f"      - {tag['name']}: {tag['count']} records")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Clear Database Frontend Test")
    print("=" * 60)
    
    # Check current state
    print("\n1️⃣ Current Database State:")
    total = check_database()
    
    if total == 0:
        print("\n   Database is empty. Adding test data...")
        add_test_data()
        total = check_database()
    
    # Verify tags endpoint
    verify_tags_endpoint()
    
    print("\n" + "=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("1. Open web UI: http://localhost:9999/")
    print("2. Verify tags are visible in left sidebar")
    print("3. Click 'Clear Database' button")
    print("4. Confirm the action")
    print("5. After clearing:")
    print("   - Tags sidebar should show: 'No tags found. Ingest data first.'")
    print("   - Records area should show: 'Database cleared. Import new CSV...'")
    print("6. Hard refresh browser (Ctrl+Shift+R) if old data still visible")
    print("=" * 60)
