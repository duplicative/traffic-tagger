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


def run_correlation_for_url(url: str):
    """
    Background task to run correlation analysis for a specific URL.
    Finds all HTTP records matching the URL and applies correlation rules.
    
    Args:
        url: The URL from enrichment event to correlate
    """
    if not rule_engine:
        return
    
    try:
        # Normalize the enrichment event URL
        normalized_url = normalize_url_for_matching(url)
        
        print(f"[Correlation] Processing URL: {normalized_url}")
        
        # Find all HTTP records that match this URL
        # Need to reconstruct URL from HTTP record fields and match
        matching_records = []
        for record in collection.find({}):
            record_url = rule_engine.normalize_url(record)
            if record_url == normalized_url:
                matching_records.append(record)
        
        print(f"[Correlation] Found {len(matching_records)} matching HTTP records")
        
        # Run correlation analysis on each matching record
        for record in matching_records:
            new_tags, highlights = rule_engine.run_correlation_analysis(record)
            
            if new_tags:
                print(f"[Correlation] Adding tags to record {record.get('_id')}: {new_tags}")
                
                # Update the record with new tags and highlights
                existing_tags = record.get('tags', [])
                existing_highlights = record.get('highlights', {})
                
                # Merge tags (avoid duplicates)
                updated_tags = list(set(existing_tags + new_tags))
                
                # Merge highlights
                updated_highlights = {**existing_highlights, **highlights}
                
                # Update MongoDB
                collection.update_one(
                    {"_id": record["_id"]},
                    {"$set": {
                        "tags": updated_tags,
                        "highlights": updated_highlights,
                        "correlation_processed_at": datetime.utcnow().isoformat()
                    }}
                )
                
                print(f"[Correlation] Updated record {record.get('_id')} with {len(new_tags)} new tags")
    
    except Exception as e:
        print(f"[Correlation] Error processing URL {url}: {e}")
        import traceback
        traceback.print_exc()


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
