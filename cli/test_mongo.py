import sys
from pymongo import MongoClient

mongo_uri = "mongodb://database:27017/"
try:
    client = MongoClient(mongo_uri)
    db = client.admin
    server_info = db.command('serverStatus')
    print("Connection successful!")
except Exception as e:
    print(f"Connection failed: {e}")