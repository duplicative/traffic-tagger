#!/usr/bin/env python3
"""Debug script to test rule matching."""
import os
import sys
from pymongo import MongoClient

# Add shared to path
sys.path.insert(0, '/home/guid/projects/traffic_tagger')

from shared.rule_engine import RuleEngine
from shared.http_parser import HTTPParser

# Connect to MongoDB
mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:password123@localhost:27017/')
client = MongoClient(mongo_uri)
db = client['http_tagger']
collection = db['records']

# Load rules
rule_engine = RuleEngine('/home/guid/projects/traffic_tagger/data/rules.yaml')

# Get a sample record without tags
record = collection.find_one({'tags': {'$size': 0}})
if not record:
    print("No untagged records found")
    sys.exit(0)

print(f"Testing record: {record['host']}{record['path']}")
print(f"Current tags: {record['tags']}")
print()

# Parse the request and response
request = HTTPParser.parse_request(record['decoded_request'])
response = HTTPParser.parse_response(record['decoded_response'])

print("=== Parsed Request ===")
print(f"Method: {request['method']}")
print(f"Path: {request['path']}")
print(f"Headers: {list(request['headers'].keys())}")
print(f"Body length: {len(request['body'])}")
print()

print("=== Parsed Response ===")
print(f"Status: {response['status_code']} {response['status_message']}")
print(f"Headers: {list(response['headers'].keys())}")
print(f"Body length: {len(response['body'])}")
print()

# Test each rule
print("=== Rule Matching ===")
for rule in rule_engine.rules:
    if not rule.get('enabled', True):
        continue
    
    matched = rule_engine._evaluate_rule(rule, request, response)
    print(f"{rule['name']}: {'MATCH' if matched else 'NO MATCH'}")
    
    # Show condition details
    if matched:
        for condition in rule.get('conditions', []):
            target_value = rule_engine._extract_target_value(condition['target'], request, response)
            print(f"  - {condition['target']} = {repr(target_value[:100] if target_value else None)}")

client.close()
