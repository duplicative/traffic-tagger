#!/usr/bin/env python3
"""
Setup script to create new MongoDB collections for sidecar enrichment data.
Creates: dom_snapshots, js_executions, storage_states with url indexes.
"""
import os
from pymongo import MongoClient, IndexModel, ASCENDING

# Get MongoDB URI from environment or use default
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://admin:admin@localhost:27017/")

def setup_enrichment_collections():
    """Create new collections with indexes for enrichment events"""
    client = MongoClient(MONGO_URI)
    db = client["http_tagger"]
    
    collections_to_create = [
        "dom_snapshots",
        "js_executions", 
        "storage_states"
    ]
    
    print("Setting up enrichment collections...")
    
    for collection_name in collections_to_create:
        # Create collection if it doesn't exist
        if collection_name not in db.list_collection_names():
            db.create_collection(collection_name)
            print(f"✓ Created collection: {collection_name}")
        else:
            print(f"✓ Collection already exists: {collection_name}")
        
        # Create index on url field
        collection = db[collection_name]
        index_model = IndexModel([("url", ASCENDING)], name="url_index")
        collection.create_indexes([index_model])
        print(f"✓ Created index on 'url' field for {collection_name}")
        
        # Also create index on eventId for efficient lookups
        eventid_index = IndexModel([("eventId", ASCENDING)], name="eventId_index", unique=True)
        collection.create_indexes([eventid_index])
        print(f"✓ Created unique index on 'eventId' field for {collection_name}")
    
    # Verify collections exist
    existing_collections = db.list_collection_names()
    print("\nVerification:")
    for collection_name in collections_to_create:
        if collection_name in existing_collections:
            indexes = list(db[collection_name].list_indexes())
            print(f"✓ {collection_name}: {len(indexes)} indexes")
            for idx in indexes:
                print(f"  - {idx['name']}")
        else:
            print(f"✗ {collection_name}: NOT FOUND")
    
    client.close()
    print("\nSetup complete!")

if __name__ == "__main__":
    setup_enrichment_collections()
