#!/usr/bin/env python3
"""
Test script for clear database functionality.
Tests the new DELETE /api/clear-all endpoint.
"""
import requests
from pymongo import MongoClient

API_URL = "http://localhost:8000/api/clear-all"
MONGO_URI = "mongodb://admin:password123@localhost:27017/"

def check_database_counts():
    """Check current record counts in database"""
    client = MongoClient(MONGO_URI)
    db = client["http_tagger"]
    
    collections = [
        "records",
        "dom_snapshots",
        "js_executions",
        "storage_states",
        "watcher_metadata"
    ]
    
    counts = {}
    total = 0
    
    for collection_name in collections:
        count = db[collection_name].count_documents({})
        counts[collection_name] = count
        total += count
    
    client.close()
    return counts, total

def test_clear_database():
    """Test the clear database endpoint"""
    print("=" * 60)
    print("Clear Database Functionality Test")
    print("=" * 60)
    
    # Check initial counts
    print("\n📊 Current Database State:")
    initial_counts, initial_total = check_database_counts()
    for collection, count in initial_counts.items():
        print(f"   {collection}: {count} records")
    print(f"   Total: {initial_total} records")
    
    if initial_total == 0:
        print("\n⚠️  Database is already empty. Add some test data first.")
        print("   Run: python test_phase1_integration.py")
        return False
    
    # Ask for confirmation
    print("\n⚠️  WARNING: This will DELETE ALL records from the database!")
    response = input("   Type 'YES' to proceed: ")
    
    if response != 'YES':
        print("\n❌ Test cancelled.")
        return False
    
    # Call clear endpoint
    print("\n🗑️  Clearing database...")
    
    try:
        api_response = requests.delete(API_URL)
        
        if api_response.ok:
            result = api_response.json()
            print("✅ Success!")
            print(f"   {result['message']}")
            print("\n   Details:")
            for collection, count in result['details'].items():
                print(f"      {collection}: {count} deleted")
        else:
            print(f"❌ Error: {api_response.status_code}")
            print(f"   {api_response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Is the API service running?")
        print("   Try: docker compose up -d")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    # Verify database is empty
    print("\n🔍 Verifying database state...")
    final_counts, final_total = check_database_counts()
    
    if final_total == 0:
        print("✅ Database successfully cleared!")
        print("\n📊 Final Database State:")
        for collection, count in final_counts.items():
            print(f"   {collection}: {count} records")
        return True
    else:
        print(f"⚠️  Warning: Database still has {final_total} records")
        for collection, count in final_counts.items():
            if count > 0:
                print(f"   {collection}: {count} records")
        return False

if __name__ == "__main__":
    success = test_clear_database()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Test Complete: Database cleared successfully!")
    else:
        print("❌ Test Failed or Cancelled")
    print("=" * 60)
