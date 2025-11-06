#!/usr/bin/env python3
"""
Add normalized_url field to existing HTTP records in the database.

This script:
1. Connects to MongoDB
2. Iterates through all records in the records collection
3. Calculates normalized_url from scheme, host, path
4. Updates each record with the normalized_url field
5. Creates an index on normalized_url and response_created_at for efficient correlation queries
"""

import os
from pymongo import MongoClient
from urllib.parse import urlparse, urlunparse

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://admin:password123@localhost:27017/')
client = MongoClient(MONGO_URI)
db = client['http_tagger']
collection = db['records']

def normalize_url(record):
    """
    Construct and normalize a URL from HTTP record fields.
    Removes query parameters and fragments for flexible matching.
    """
    scheme = record.get('scheme', 'https')
    host = record.get('host', '')
    path = record.get('path', '/')
    
    # Handle authority field if present
    if not host and record.get('authority'):
        host = record.get('authority')
    
    # Construct base URL
    if not host:
        return ''
    
    # Parse to remove query and fragment
    full_url = f"{scheme}://{host}{path}"
    parsed = urlparse(full_url)
    
    # Reconstruct without query and fragment
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        '',  # params
        '',  # query (removed)
        ''   # fragment (removed)
    ))
    
    return normalized

def main():
    print("="*70)
    print("Adding normalized_url field to HTTP records")
    print("="*70)
    
    # Count total records
    total_records = collection.count_documents({})
    print(f"\nTotal HTTP records: {total_records}")
    
    # Process records
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    print("\nProcessing records...")
    for record in collection.find({}):
        try:
            # Check if normalized_url already exists
            if 'normalized_url' in record:
                skipped_count += 1
                continue
            
            # Calculate normalized URL
            normalized_url = normalize_url(record)
            
            if not normalized_url:
                print(f"  Warning: Could not normalize URL for record {record.get('_id')}")
                error_count += 1
                continue
            
            # Update record
            collection.update_one(
                {'_id': record['_id']},
                {'$set': {'normalized_url': normalized_url}}
            )
            
            updated_count += 1
            
            if updated_count % 100 == 0:
                print(f"  Processed {updated_count} records...")
        
        except Exception as e:
            print(f"  Error processing record {record.get('_id')}: {e}")
            error_count += 1
    
    print(f"\nUpdate complete!")
    print(f"  Updated: {updated_count}")
    print(f"  Skipped (already had normalized_url): {skipped_count}")
    print(f"  Errors: {error_count}")
    
    # Create indexes
    print("\nCreating indexes...")
    
    # Index on normalized_url for URL lookups
    collection.create_index('normalized_url')
    print("  ✓ Created index on 'normalized_url'")
    
    # Compound index on (normalized_url, response_created_at) for temporal correlation
    collection.create_index([
        ('normalized_url', 1),
        ('response_created_at', 1)
    ])
    print("  ✓ Created compound index on ('normalized_url', 'response_created_at')")
    
    # Show index statistics
    indexes = list(collection.list_indexes())
    print(f"\nTotal indexes on records collection: {len(indexes)}")
    for idx in indexes:
        print(f"  - {idx['name']}: {idx.get('key', {})}")
    
    print("\n" + "="*70)
    print("Migration complete!")
    print("="*70)

if __name__ == "__main__":
    main()
