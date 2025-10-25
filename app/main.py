from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import os
from bson import ObjectId

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mongo_uri = os.getenv('MONGO_URI')
client = MongoClient(mongo_uri)
db = client.get_database()
collection = db['records']

@app.get("/api/tags")
def get_tags():
    pipeline = [
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    result = list(collection.aggregate(pipeline))
    tags = [{"name": r["_id"], "count": r["count"]} for r in result]
    return {"tags": tags}

@app.get("/api/records")
def get_records(tags: str = None):
    query = {}
    if tags:
        tag_list = tags.split(',')
        query = {"tags": {"$all": tag_list}}
    records = list(collection.find(query, {
        "_id": 1,
        "source_id": 1,
        "host": 1,
        "method": 1,
        "path": 1,
        "response_status_code": 1,
        "tags": 1
    }))
    # Convert ObjectId to str
    for r in records:
        r["id"] = str(r.pop("_id"))
    return {"records": records}

@app.get("/api/record/{record_id}")
def get_record(record_id: str):
    try:
        oid = ObjectId(record_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID")
    record = collection.find_one({"_id": oid})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    record["id"] = str(record.pop("_id"))
    return record
