import typer
from pathlib import Path
import csv
import base64
import pymongo
import datetime
from .rule_engine import load_rules, apply_rules
from .http_parser import parse_http_request, parse_http_response

app = typer.Typer()

@app.command()
def ingest(
    file: Path = typer.Option(..., help="Path to CSV file"),
    rules: Path = typer.Option(..., help="Path to YAML rules file"),
    mongo_uri: str = typer.Option(..., help="MongoDB connection string")
):
    # Load rules
    rules_list = load_rules(str(rules))

    # Connect to Mongo
    client = pymongo.MongoClient(mongo_uri)
    db = client.get_database()
    collection = db['records']

    # Ensure indexes
    collection.create_index('tags')
    collection.create_index('source_id', unique=True)
    collection.create_index('host')

    # Count total rows
    with open(file, 'r') as f:
        reader = csv.DictReader(f)
        total = sum(1 for row in reader)

    # Process
    with open(file, 'r') as f:
        reader = csv.DictReader(f)
        processed = 0
        inserted = 0
        updated = 0
        tagged = 0
        for row in reader:
            processed += 1
            source_id = int(row['id'])
            host = row['host']

            # Decode
            decoding_error_request = False
            decoding_error_response = False
            try:
                decoded_request = base64.b64decode(row['raw']).decode('utf-8')
            except:
                decoded_request = None
                decoding_error_request = True

            try:
                decoded_response = base64.b64decode(row['response_raw']).decode('utf-8')
            except:
                decoded_response = None
                decoding_error_response = True

            # Parse
            request_data = parse_http_request(decoded_request) if decoded_request else {}
            response_data = parse_http_response(decoded_response) if decoded_response else {}

            # Build record
            record = {
                'source_id': source_id,
                'host': host,
                'method': request_data.get('method'),
                'path': request_data.get('path'),
                'response_status_code': response_data.get('status_code'),
                **{k: v for k, v in row.items() if k != 'id'},  # all original except id
                'decoded_request': decoded_request,
                'decoded_response': decoded_response,
                'processed_at': datetime.datetime.utcnow().isoformat()
            }
            if decoding_error_request:
                record['decoding_error_request'] = True
            if decoding_error_response:
                record['decoding_error_response'] = True

            # Apply rules
            parsed_record = {'request': request_data, 'response': response_data}
            tags = apply_rules(rules_list, parsed_record)
            record['tags'] = tags
            if tags:
                tagged += 1

            # Insert or update
            try:
                collection.insert_one(record)
                inserted += 1
            except pymongo.errors.DuplicateKeyError:
                collection.replace_one({'source_id': source_id}, record)
                updated += 1

            # Progress every 100
            if processed % 100 == 0 or processed == total:
                print(f"Processed {processed}/{total}")

        print(f"Ingestion Complete.\n- Records Processed: {processed}\n- Records Inserted: {inserted}\n- Records Updated: {updated}\n- Records with Tags: {tagged}")

if __name__ == "__main__":
    app()
