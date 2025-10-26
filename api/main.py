from fastapi import FastAPI
import os
from pymongo import MongoClient
from typing import List, Optional
from bson import ObjectId

app = FastAPI()

mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client.http_tagger
records_collection = db.records

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/api/tags")
def get_tags():
    pipeline = [
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$project": {"name": "$_id", "count": 1, "_id": 0}}
    ]
    tags = list(records_collection.aggregate(pipeline))
    return {"tags": tags}

@app.get("/api/records")
def get_records(tags: Optional[str] = None):
    query = {}
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
        query = {"tags": {"$all": tag_list}}
    
    records = list(records_collection.find(query, {
        "_id": 1,
        "source_id": 1,
        "host": 1,
        "method": 1,
        "path": 1,
        "response.status_code": 1,
        "tags": 1
    }))

    # Convert ObjectId to string
    for record in records:
        record["_id"] = str(record["_id"])
        if 'response' in record and 'status_code' in record['response']:
            record['response_status_code'] = record['response']['status_code']
            del record['response']

    return {"records": records}

@app.get("/api/record/{record_id}")
def get_record(record_id: str):
    try:
        oid = ObjectId(record_id)
    except Exception:
        return {"error": "Invalid ObjectId"}

    record = records_collection.find_one({"_id": oid})
    if record:
        record["_id"] = str(record["_id"])
        return record
    return {"error": "Record not found"}
