"""FastAPI backend for HTTP Traffic Tagger."""
import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
from pydantic import BaseModel, Field

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
    processed_at: str


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
            "processed_at": doc.get("processed_at", "")
        }
        
        return record
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching record: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
