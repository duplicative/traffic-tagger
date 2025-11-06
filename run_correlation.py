#!/usr/bin/env python3
"""
Run Correlation Engine

Executes temporal-URL correlation on all HTTP records in the database,
matching sidecar enrichment events to their originating HTTP requests.
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from main import run_correlation_for_url


def main():
    """Execute correlation on all HTTP records"""
    
    # Connect to MongoDB
    # When running from host (not Docker), use localhost with credentials
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:password123@localhost:27017/')
    print(f"Connecting to MongoDB: {mongo_uri.replace('password123', '***')}")
    
    client = MongoClient(mongo_uri)
    db = client['http_tagger']
    records_collection = db['records']
    
    # Get statistics before correlation
    total_records = records_collection.count_documents({})
    print(f"\nTotal HTTP records: {total_records}")
    
    if total_records == 0:
        print("No HTTP records found. Nothing to correlate.")
        return
    
    # Get unique URLs
    urls = records_collection.distinct('normalized_url')
    print(f"Unique URLs to process: {len(urls)}")
    
    # Get enrichment events counts
    dom_count = db['dom_snapshots'].count_documents({})
    js_count = db['js_executions'].count_documents({})
    storage_count = db['storage_states'].count_documents({})
    total_events = dom_count + js_count + storage_count
    
    print(f"\nEnrichment events available:")
    print(f"  - DOM snapshots: {dom_count}")
    print(f"  - JS executions: {js_count}")
    print(f"  - Storage states: {storage_count}")
    print(f"  - Total: {total_events}")
    
    if total_events == 0:
        print("\nNo enrichment events found. Nothing to correlate.")
        print("Make sure the sidecar extension has captured some events first.")
        return
    
    print("\n" + "="*60)
    print("STARTING CORRELATION")
    print("="*60)
    
    # Process each URL
    processed_urls = 0
    total_correlated = 0
    
    for i, url in enumerate(urls, 1):
        if not url:
            continue
            
        print(f"\n[{i}/{len(urls)}] Processing: {url[:80]}...")
        
        try:
            # Run correlation for this URL
            result = run_correlation_for_url(url)
            
            if result['success']:
                num_correlated = result.get('records_updated', 0)
                total_correlated += num_correlated
                processed_urls += 1
                
                if num_correlated > 0:
                    print(f"  ✓ Correlated {num_correlated} records")
                else:
                    print(f"  - No events matched")
            else:
                print(f"  ✗ Error: {result.get('message', 'Unknown error')}")
        
        except Exception as e:
            print(f"  ✗ Exception: {str(e)}")
    
    print("\n" + "="*60)
    print("CORRELATION COMPLETE")
    print("="*60)
    
    # Get statistics after correlation
    records_with_events = records_collection.count_documents({
        'correlated_events': {'$exists': True, '$ne': []}
    })
    
    correlation_rate = (records_with_events / total_records * 100) if total_records > 0 else 0
    
    print(f"\nResults:")
    print(f"  - URLs processed: {processed_urls}/{len(urls)}")
    print(f"  - Records with correlated events: {records_with_events}/{total_records}")
    print(f"  - Correlation rate: {correlation_rate:.1f}%")
    print(f"  - Total correlations made: {total_correlated}")
    
    # Show sample correlated record
    sample = records_collection.find_one({
        'correlated_events': {'$exists': True, '$ne': []}
    })
    
    if sample:
        print(f"\nSample correlated record:")
        print(f"  - ID: {sample['_id']}")
        print(f"  - URL: {sample.get('normalized_url', 'N/A')[:80]}")
        print(f"  - Events: {len(sample.get('correlated_events', []))}")
        print(f"  - Window: {sample.get('correlation_window', {})}")
    
    print(f"\n✓ Correlation complete!")
    print(f"\nNext steps:")
    print(f"  1. Open http://localhost:9999/")
    print(f"  2. Click 'Correlation Timeline' tab")
    print(f"  3. View correlated events")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
