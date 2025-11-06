"""FastAPI backend for HTTP Traffic Tagger."""
import os
import asyncio
from typing import List, Optional, Dict, Any, Set
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
from pydantic import BaseModel, Field
from datetime import datetime
from urllib.parse import urlparse, urlunparse
import sys
sys.path.append('/app')
from shared.rule_engine import RuleEngine

app = FastAPI(title="HTTP Traffic Tagger API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URI)
db = client['http_tagger']
collection = db['records']

# Initialize Rule Engine with MongoDB client for correlation
RULES_FILE = os.getenv('RULES_FILE', '/data/rules.yaml')
try:
    rule_engine = RuleEngine(RULES_FILE, db_client=client)
    print(f"[API] Rule engine initialized with correlation support")
    print(f"[API] Loaded {len(rule_engine.correlation_rules)} correlation rules")
except Exception as e:
    print(f"[API] Warning: Could not initialize rule engine: {e}")
    rule_engine = None

# Correlation task queue
correlation_queue: asyncio.Queue = asyncio.Queue()
processed_urls: Set[str] = set()  # Track recently processed URLs to avoid duplicates


class TagInfo(BaseModel):
    """Tag information model."""
    name: str
    count: int


class RecordSummary(BaseModel):
    """Record summary model."""
    id: str
    source_id: int
    host: str
    method: str
    path: str
    response_status_code: int
    tags: List[str]


class RecordDetail(BaseModel):
    """Full record detail model."""
    id: str
    source_id: int
    host: str
    method: str
    path: str
    http_version: str
    scheme: str
    authority: str
    request_content_length: int
    request_timestamp_start: int
    request_timestamp_end: int
    response_status_code: int
    response_reason: str
    response_content_length: int
    response_timestamp_start: int
    response_timestamp_end: int
    response_created_at: int
    decoded_request: str
    request_decoding_error: bool
    decoded_response: str
    response_decoding_error: bool
    tags: List[str]
    highlights: Dict[str, List[str]] = {}
    processed_at: str


class EnrichmentEvent(BaseModel):
    """Enrichment event model from sidecar-extension."""
    eventId: str
    timestamp: str
    eventType: str
    url: str
    data: Dict[str, Any]


class EnrichmentEventsRequest(BaseModel):
    """Request body for enrichment events endpoint."""
    events: List[EnrichmentEvent]


def normalize_url_for_matching(url: str) -> str:
    """
    Normalize a URL by removing query parameters and fragments.
    
    Args:
        url: Full URL string
        
    Returns:
        Normalized URL without query/fragment
    """
    parsed = urlparse(url)
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        '',  # params
        '',  # query (removed)
        ''   # fragment (removed)
    ))
    return normalized


def parse_iso_timestamp(iso_string: str) -> float:
    """
    Parse ISO 8601 timestamp string to Unix timestamp (seconds).
    
    Args:
        iso_string: ISO 8601 formatted timestamp
        
    Returns:
        Unix timestamp in seconds
    """
    from dateutil import parser
    dt = parser.isoparse(iso_string)
    return dt.timestamp()


def find_preceding_http_record(event_url: str, event_timestamp: float, normalized_url: str):
    """
    Find the HTTP record that immediately precedes this sidecar event.
    
    Algorithm:
    1. Find all HTTP records with matching normalized URL
    2. Filter to records where response_created_at <= event_timestamp
    3. Sort by response_created_at descending
    4. Return the first (most recent before event)
    
    Args:
        event_url: Original event URL (for logging)
        event_timestamp: Event timestamp in seconds
        normalized_url: Normalized URL for matching
        
    Returns:
        HTTP record dict or None
    """
    # Find matching records that occurred BEFORE the event
    matching_records = list(collection.find({
        'normalized_url': normalized_url,
        'response_created_at': {'$lte': event_timestamp}
    }).sort('response_created_at', -1).limit(1))
    
    return matching_records[0] if matching_records else None


def get_correlation_window(http_record, normalized_url):
    """
    Calculate the time window for this HTTP record.
    Window extends from record time to next HTTP record time (or infinity).
    
    Args:
        http_record: The HTTP record
        normalized_url: Normalized URL to find next record
        
    Returns:
        Tuple of (start_timestamp, end_timestamp)
    """
    start_time = http_record['response_created_at']
    
    # Find next HTTP record for same URL
    next_records = list(collection.find({
        'normalized_url': normalized_url,
        'response_created_at': {'$gt': start_time}
    }).sort('response_created_at', 1).limit(1))
    
    if next_records:
        end_time = next_records[0]['response_created_at']
    else:
        end_time = float('inf')
    
    return (start_time, end_time)


def run_correlation_for_url(url: str):
    """
    Background task implementing temporal-URL correlation strategy.
    
    Algorithm:
    1. Get all sidecar events for this URL, sorted by timestamp
    2. For each event, find the HTTP record that immediately precedes it
    3. Calculate time window for that HTTP record
    4. Run correlation rules on events within that time window
    5. Update HTTP record with correlation results
    
    Args:
        url: The URL from enrichment event to correlate
        
    Returns:
        Dict with 'success', 'records_updated', and optional 'message' keys
    """
    if not rule_engine:
        return {'success': False, 'message': 'Rule engine not initialized', 'records_updated': 0}
    
    try:
        # Normalize the event URL
        normalized_url = normalize_url_for_matching(url)
        
        print(f"[Correlation] Processing URL: {normalized_url}")
        
        # Collect all events for this URL from all enrichment collections
        all_events = []
        for coll_name in ['dom_snapshots', 'js_executions', 'storage_states']:
            events = list(db[coll_name].find({'url': url}))
            for event in events:
                event['_collection'] = coll_name
                all_events.append(event)
        
        print(f"[Correlation] Found {len(all_events)} sidecar events")
        
        if not all_events:
            return {'success': True, 'records_updated': 0, 'message': 'No events found for URL'}
        
        # Sort events by timestamp
        all_events.sort(key=lambda e: parse_iso_timestamp(e['timestamp']))
        
        # Group events by their preceding HTTP record
        record_events_map = {}  # record_id -> list of events
        
        for event in all_events:
            event_timestamp = parse_iso_timestamp(event['timestamp'])
            
            # Find the HTTP record that this event belongs to
            http_record = find_preceding_http_record(url, event_timestamp, normalized_url)
            
            if http_record:
                record_id = str(http_record['_id'])
                if record_id not in record_events_map:
                    record_events_map[record_id] = {
                        'record': http_record,
                        'events': []
                    }
                record_events_map[record_id]['events'].append(event)
            else:
                print(f"[Correlation] No matching HTTP record found for event {event['eventId']} at {event['timestamp']}")
        
        print(f"[Correlation] Events mapped to {len(record_events_map)} HTTP records")
        
        # Process each HTTP record with its correlated events
        for record_id, data in record_events_map.items():
            http_record = data['record']
            correlated_events = data['events']
            
            # Get time window for this HTTP record
            window_start, window_end = get_correlation_window(http_record, normalized_url)
            
            print(f"[Correlation] Processing record {record_id} with {len(correlated_events)} events")
            print(f"[Correlation] Time window: {window_start} to {window_end}")
            
            # Run correlation rules with time window
            new_tags, highlights = rule_engine.run_correlation_analysis(
                http_record,
                window_start,
                window_end
            )
            
            if new_tags:
                print(f"[Correlation] Adding {len(new_tags)} tags to record {record_id}: {new_tags}")
                
                # Prepare correlation metadata
                correlated_events_metadata = []
                for event in correlated_events:
                    correlated_events_metadata.append({
                        'eventId': event['eventId'],
                        'eventType': event['eventType'],
                        'timestamp': event['timestamp'],
                        'collection': event['_collection']
                    })
                
                # Update the record with new tags, highlights, and metadata
                existing_tags = http_record.get('tags', [])
                existing_highlights = http_record.get('highlights', {})
                
                # Merge tags (avoid duplicates)
                updated_tags = list(set(existing_tags + new_tags))
                
                # Merge highlights
                updated_highlights = {**existing_highlights, **highlights}
                
                # Update MongoDB
                collection.update_one(
                    {"_id": http_record["_id"]},
                    {"$set": {
                        "tags": updated_tags,
                        "highlights": updated_highlights,
                        "correlation_processed_at": datetime.utcnow().isoformat(),
                        "correlated_events": correlated_events_metadata,
                        "correlation_window": {
                            "start": window_start,
                            "end": window_end if window_end != float('inf') else None
                        }
                    }}
                )
                
                print(f"[Correlation] Updated record {record_id} with {len(new_tags)} new tags")
        
        return {
            'success': True,
            'records_updated': len(record_events_map),
            'message': f'Correlated {len(record_events_map)} records'
        }
    
    except Exception as e:
        print(f"[Correlation] Error processing URL {url}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': str(e),
            'records_updated': 0
        }


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "HTTP Traffic Tagger API", "version": "1.0"}


@app.get("/api/tags")
async def get_tags():
    """
    Get all unique tags with their counts.
    
    Returns:
        Dictionary with tags list containing name and count for each tag
    """
    try:
        # Use aggregation to get unique tags with counts
        pipeline = [
            {"$unwind": "$tags"},
            {"$group": {
                "_id": "$tags",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$project": {
                "_id": 0,
                "name": "$_id",
                "count": 1
            }}
        ]
        
        results = list(collection.aggregate(pipeline))
        
        return {"tags": results}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tags: {str(e)}")


@app.get("/api/records")
async def get_records(tags: Optional[str] = Query(None)):
    """
    Get records filtered by tags.
    
    Args:
        tags: Comma-separated list of tag names (AND logic)
        
    Returns:
        Dictionary with records list
    """
    try:
        query = {}
        
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            # AND logic: record must have all specified tags
            query["tags"] = {"$all": tag_list}
        
        # Fetch records with only summary fields
        records = []
        for doc in collection.find(query).limit(1000):
            records.append({
                "id": str(doc["_id"]),
                "source_id": doc.get("source_id", 0),
                "host": doc.get("host", ""),
                "method": doc.get("method", ""),
                "path": doc.get("path", ""),
                "response_status_code": doc.get("response_status_code", 0),
                "tags": doc.get("tags", [])
            })
        
        return {"records": records}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching records: {str(e)}")


@app.get("/api/record/{record_id}")
async def get_record(record_id: str):
    """
    Get full details for a single record.
    
    Args:
        record_id: MongoDB ObjectId of the record
        
    Returns:
        Full record details
    """
    try:
        # Validate ObjectId
        try:
            obj_id = ObjectId(record_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid record ID format")
        
        # Fetch the record
        doc = collection.find_one({"_id": obj_id})
        
        if not doc:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Convert to response model
        record = {
            "id": str(doc["_id"]),
            "source_id": doc.get("source_id", 0),
            "host": doc.get("host", ""),
            "method": doc.get("method", ""),
            "path": doc.get("path", ""),
            "http_version": doc.get("http_version", ""),
            "scheme": doc.get("scheme", ""),
            "authority": doc.get("authority", ""),
            "request_content_length": doc.get("request_content_length", 0),
            "request_timestamp_start": doc.get("request_timestamp_start", 0),
            "request_timestamp_end": doc.get("request_timestamp_end", 0),
            "response_status_code": doc.get("response_status_code", 0),
            "response_reason": doc.get("response_reason", ""),
            "response_content_length": doc.get("response_content_length", 0),
            "response_timestamp_start": doc.get("response_timestamp_start", 0),
            "response_timestamp_end": doc.get("response_timestamp_end", 0),
            "response_created_at": doc.get("response_created_at", 0),
            "decoded_request": doc.get("decoded_request", ""),
            "request_decoding_error": doc.get("request_decoding_error", False),
            "decoded_response": doc.get("decoded_response", ""),
            "response_decoding_error": doc.get("response_decoding_error", False),
            "tags": doc.get("tags", []),
            "highlights": doc.get("highlights", {}),
            "processed_at": doc.get("processed_at", "")
        }
        
        return record
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching record: {str(e)}")


@app.post("/api/enrichment-events")
async def post_enrichment_events(request: EnrichmentEventsRequest, background_tasks: BackgroundTasks):
    """
    Receive and store enrichment events from sidecar-extension.
    Triggers correlation analysis in background.
    
    Args:
        request: EnrichmentEventsRequest containing list of events
        background_tasks: FastAPI background tasks for async correlation
        
    Returns:
        Success message with count of stored events
    """
    try:
        stored_counts = {
            "dom_snapshots": 0,
            "js_executions": 0,
            "storage_states": 0
        }
        
        event_urls = set()
        
        for event in request.events:
            # Convert Pydantic model to dict
            event_dict = event.dict()
            
            # Route event to appropriate collection based on eventType
            if event.eventType == "DOM_SNAPSHOT":
                target_collection = db["dom_snapshots"]
                stored_counts["dom_snapshots"] += 1
            elif event.eventType == "JS_EXECUTION":
                target_collection = db["js_executions"]
                stored_counts["js_executions"] += 1
            elif event.eventType == "STORAGE_STATE":
                target_collection = db["storage_states"]
                stored_counts["storage_states"] += 1
            else:
                # Skip unknown event types
                continue
            
            # Add received timestamp
            event_dict["received_at"] = datetime.utcnow().isoformat()
            
            # Upsert by eventId to handle duplicates
            target_collection.update_one(
                {"eventId": event.eventId},
                {"$set": event_dict},
                upsert=True
            )
            
            # Collect URL for correlation analysis
            event_urls.add(event.url)
        
        # Queue correlation tasks for each unique URL
        if rule_engine and event_urls:
            for url in event_urls:
                background_tasks.add_task(run_correlation_for_url, url)
        
        return {
            "status": "success",
            "message": f"Stored {sum(stored_counts.values())} events",
            "details": stored_counts,
            "correlation_queued": len(event_urls) if rule_engine else 0
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing enrichment events: {str(e)}")


@app.get("/api/raw-records")
async def get_raw_records(
    source: Optional[str] = Query(None, enum=["csv", "sidecar"]),
    category: Optional[str] = Query(None, enum=["dom_snapshots", "js_executions", "storage_states"]),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Get raw records from the database with filtering and pagination.
    
    Args:
        source: Filter by record source (csv or sidecar)
        category: Filter by sidecar record category (only for sidecar source)
        page: Page number for pagination
        page_size: Number of records per page (max 100)
        
    Returns:
        Dictionary with records list, pagination info, source, and category
    """
    try:
        skip = (page - 1) * page_size
        records = []
        total_records = 0
        actual_source = source or "csv"  # Default to CSV if no source specified
        actual_category = None
        
        if source == "csv" or not source:
            # Fetch from records collection (CSV data)
            target_collection = db["records"]
            actual_source = "csv"
            
            for doc in target_collection.find({}).skip(skip).limit(page_size):
                # Convert ObjectId to string for JSON serialization
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                records.append(doc)
            
            total_records = target_collection.count_documents({})
            
        elif source == "sidecar":
            # Fetch from enrichment collections
            if category:
                # Specific category requested
                target_collection = db[category]
                actual_category = category
                
                for doc in target_collection.find({}).skip(skip).limit(page_size):
                    if "_id" in doc:
                        doc["_id"] = str(doc["_id"])
                    records.append(doc)
                
                total_records = target_collection.count_documents({})
            else:
                # No category specified - fetch from all enrichment collections
                collections_to_query = ["dom_snapshots", "js_executions", "storage_states"]
                all_records = []
                
                for coll_name in collections_to_query:
                    coll = db[coll_name]
                    for doc in coll.find({}):
                        if "_id" in doc:
                            doc["_id"] = str(doc["_id"])
                        doc["_collection"] = coll_name  # Add source collection info
                        all_records.append(doc)
                
                # Sort by timestamp if available
                all_records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                
                # Calculate pagination
                total_records = len(all_records)
                records = all_records[skip:skip + page_size]
        
        total_pages = max(1, (total_records + page_size - 1) // page_size)
        
        return {
            "records": records,
            "total_records": total_records,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
            "source": actual_source,
            "category": actual_category
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching raw records: {str(e)}")


@app.get("/api/correlation-timeline")
async def get_correlation_timeline(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    url_filter: Optional[str] = Query(None)
):
    """
    Get correlation timeline showing HTTP records with their correlated sidecar events.
    
    Args:
        page: Page number for pagination
        page_size: Number of records per page
        url_filter: Optional URL filter (partial match)
        
    Returns:
        Timeline data with HTTP records and nested correlated events
    """
    try:
        skip = (page - 1) * page_size
        
        # Build query
        query = {}
        if url_filter:
            query['normalized_url'] = {'$regex': url_filter, '$options': 'i'}
        
        # Get HTTP records sorted by timestamp
        records_cursor = collection.find(query).sort('response_created_at', 1).skip(skip).limit(page_size)
        total_records = collection.count_documents(query)
        
        timeline = []
        
        for record in records_cursor:
            # Build timeline entry
            entry = {
                'http_record': {
                    'id': str(record['_id']),
                    'method': record.get('method', ''),
                    'url': record.get('normalized_url', ''),
                    'host': record.get('host', ''),
                    'path': record.get('path', ''),
                    'status': record.get('response_status_code', 0),
                    'timestamp': record.get('response_created_at', 0),
                    'tags': record.get('tags', [])
                },
                'correlated_events': [],
                'correlation_window': record.get('correlation_window', {}),
                'statistics': {
                    'total_events': 0,
                    'event_types': {},
                    'tags_added': 0
                }
            }
            
            # Process correlated events
            correlated_events_metadata = record.get('correlated_events', [])
            for event_meta in correlated_events_metadata:
                # Parse timestamp to calculate time delta
                try:
                    from dateutil import parser as date_parser
                    event_dt = date_parser.isoparse(event_meta['timestamp'])
                    event_timestamp = event_dt.timestamp()
                    time_delta = int(event_timestamp - record['response_created_at'])
                except:
                    time_delta = 0
                
                event_entry = {
                    'eventId': event_meta['eventId'],
                    'eventType': event_meta['eventType'],
                    'timestamp': event_meta['timestamp'],
                    'time_delta': time_delta,
                    'collection': event_meta.get('collection', '')
                }
                
                entry['correlated_events'].append(event_entry)
                
                # Update statistics
                event_type = event_meta['eventType']
                if event_type not in entry['statistics']['event_types']:
                    entry['statistics']['event_types'][event_type] = 0
                entry['statistics']['event_types'][event_type] += 1
            
            entry['statistics']['total_events'] = len(correlated_events_metadata)
            
            # Count correlation-added tags (tags not present initially)
            correlation_highlights = record.get('highlights', {})
            entry['statistics']['tags_added'] = len([t for t in record.get('tags', []) if t in correlation_highlights])
            
            timeline.append(entry)
        
        # Calculate summary statistics
        total_http_records = collection.count_documents({})
        records_with_events = collection.count_documents({'correlated_events': {'$exists': True, '$ne': []}})
        
        return {
            'timeline': timeline,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_records': total_records,
                'total_pages': (total_records + page_size - 1) // page_size
            },
            'summary': {
                'total_http_records': total_http_records,
                'records_with_events': records_with_events,
                'records_without_events': total_http_records - records_with_events
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching correlation timeline: {str(e)}")


@app.get("/api/correlation-stats")
async def get_correlation_stats():
    """
    Get correlation statistics and metrics.
    
    Returns:
        Statistics about correlation coverage and effectiveness
    """
    try:
        # HTTP records statistics
        total_http_records = collection.count_documents({})
        records_with_events = collection.count_documents({'correlated_events': {'$exists': True, '$ne': []}})
        
        # Calculate average events per record
        pipeline = [
            {'$match': {'correlated_events': {'$exists': True}}},
            {'$project': {'event_count': {'$size': {'$ifNull': ['$correlated_events', []]}}}},
            {'$group': {
                '_id': None,
                'avg_events': {'$avg': '$event_count'},
                'max_events': {'$max': '$event_count'}
            }}
        ]
        
        agg_result = list(collection.aggregate(pipeline))
        avg_events = agg_result[0]['avg_events'] if agg_result else 0
        max_events = agg_result[0]['max_events'] if agg_result else 0
        
        # Enrichment events statistics
        total_enrichment_events = (
            db['dom_snapshots'].count_documents({}) +
            db['js_executions'].count_documents({}) +
            db['storage_states'].count_documents({})
        )
        
        return {
            'http_records': {
                'total': total_http_records,
                'with_correlated_events': records_with_events,
                'without_events': total_http_records - records_with_events,
                'correlation_rate': round(records_with_events / total_http_records * 100, 2) if total_http_records > 0 else 0
            },
            'enrichment_events': {
                'total': total_enrichment_events,
                'dom_snapshots': db['dom_snapshots'].count_documents({}),
                'js_executions': db['js_executions'].count_documents({}),
                'storage_states': db['storage_states'].count_documents({})
            },
            'correlation_metrics': {
                'avg_events_per_record': round(avg_events, 2),
                'max_events_per_record': max_events
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching correlation stats: {str(e)}")


@app.delete("/api/clear-all")
async def clear_all_records():
    """
    Clear all records from all collections in the database.
    This allows users to start fresh analysis with new data.
    
    Returns:
        Success message with count of deleted records
    """
    try:
        deleted_counts = {}
        
        # List of all collections to clear
        collections_to_clear = [
            "records",           # HTTP traffic records
            "dom_snapshots",     # Client-side DOM events
            "js_executions",     # Client-side JS execution events
            "storage_states",    # Client-side storage events
            "watcher_metadata"   # Watcher tracking metadata
        ]
        
        total_deleted = 0
        
        for collection_name in collections_to_clear:
            collection = db[collection_name]
            result = collection.delete_many({})
            deleted_counts[collection_name] = result.deleted_count
            total_deleted += result.deleted_count
        
        return {
            "status": "success",
            "message": f"Cleared {total_deleted} total records from database",
            "details": deleted_counts
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing database: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
