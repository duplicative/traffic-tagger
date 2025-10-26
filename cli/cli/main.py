import typer
import csv
import base64
from pymongo import MongoClient
from tqdm import tqdm
import yaml
import re
import os
from email.parser import BytesParser

app = typer.Typer()

def parse_http_message(message, message_type):
    if not message:
        return None, None, None

    if message_type == 'request':
        try:
            # Find the end of the headers
            headers_end = message.find('\r\n\r\n')
            if headers_end == -1:
                return None, None, None # Invalid format

            # Split request line and headers
            request_line_end = message.find('\r\n')
            request_line = message[:request_line_end]
            headers_str = message[request_line_end+2:headers_end]
            body = message[headers_end+4:]

            # Parse request line
            parts = request_line.split(' ')
            method = parts[0]
            path = parts[1]
            http_version = parts[2]

            # Parse headers
            headers = {}
            for line in headers_str.split('\r\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()

            return {'method': method, 'path': path, 'http_version': http_version, 'headers': headers, 'body': body}, None
        except Exception as e:
            return None, f"Error parsing request: {e}"

    elif message_type == 'response':
        try:
            # Find the end of the headers
            headers_end = message.find('\r\n\r\n')
            if headers_end == -1:
                return None, None # Invalid format

            # Split status line and headers
            status_line_end = message.find('\r\n')
            status_line = message[:status_line_end]
            headers_str = message[status_line_end+2:headers_end]
            body = message[headers_end+4:]

            # Parse status line
            parts = status_line.split(' ', 2)
            http_version = parts[0]
            status_code = int(parts[1])
            status_message = parts[2]

            # Parse headers
            headers = {}
            for line in headers_str.split('\r\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()

            return {'http_version': http_version, 'status_code': status_code, 'status_message': status_message, 'headers': headers, 'body': body}, None
        except Exception as e:
            return None, f"Error parsing response: {e}"

def get_target_value(record, target):
    parts = target.split('.')
    value = record
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part.lower())
        else:
            return None
    return value

def apply_rules(record, rules):
    tags = []
    parsed_request, req_error = parse_http_message(record.get('decoded_request'), 'request')
    parsed_response, res_error = parse_http_message(record.get('decoded_response'), 'response')

    if req_error:
        print(f"Could not parse request for record {record.get('source_id')}: {req_error}")
    if res_error:
        print(f"Could not parse response for record {record.get('source_id')}: {res_error}")

    record['request'] = parsed_request
    record['response'] = parsed_response

    for rule in rules:
        if not rule.get('enabled', True):
            continue

        match_logic = rule.get('match_logic', 'AND').upper()
        conditions_met = []

        for condition in rule['conditions']:
            target_value = get_target_value(record, condition['target'])
            if target_value is None:
                conditions_met.append(False)
                continue

            op = condition['operator']
            val = condition['value']
            
            is_match = False
            if op == 'contains':
                is_match = val.lower() in str(target_value).lower()
            elif op == 'not_contains':
                is_match = val.lower() not in str(target_value).lower()
            elif op == 'equals':
                is_match = str(target_value) == val
            elif op == 'starts_with':
                is_match = str(target_value).startswith(val)
            elif op == 'ends_with':
                is_match = str(target_value).endswith(val)
            elif op == 'matches_regex':
                is_match = bool(re.search(val, str(target_value)))
            
            conditions_met.append(is_match)

        final_match = False
        if match_logic == 'AND':
            final_match = all(conditions_met)
        elif match_logic == 'OR':
            final_match = any(conditions_met)

        if final_match:
            tags.append(rule['name'])
            
    return tags

@app.command()
def ingest(
    file: str = typer.Option(..., "--file", help="Path to the CSV file to ingest."),
    rules: str = typer.Option(..., "--rules", help="Path to the YAML file with tagging rules."),
):
    mongo_uri = os.getenv("MONGO_URI")
    print(f"Ingesting file: {file}")
    print(f"Using rules: {rules}")
    print(f"Connecting to mongo: {mongo_uri}")

    try:
        with open(rules, 'r') as f:
            rule_data = yaml.safe_load(f)
        loaded_rules = rule_data.get('rules', [])
        print(f"Loaded {len(loaded_rules)} rules.")
    except FileNotFoundError:
        print(f"Error: Rules file not found at {rules}")
        raise typer.Exit(code=1)
    except Exception as e:
        print(f"Error loading rules: {e}")
        raise typer.Exit(code=1)

    try:
        client = MongoClient(mongo_uri)
        db = client.http_tagger
        records_collection = db.records
        print("Successfully connected to MongoDB.")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        raise typer.Exit(code=1)

    try:
        with open(file, 'r') as f:
            records = list(csv.DictReader(f))

        inserted_count = 0
        updated_count = 0
        tagged_count = 0

        for row in tqdm(records, desc="Processing records"):
            try:
                decoded_request = base64.b64decode(row['raw']).decode('utf-8', errors='ignore')
                row['decoded_request'] = decoded_request
            except Exception:
                row['decoded_request'] = ""
                row['decoding_error_request'] = True

            try:
                decoded_response = base64.b64decode(row['response_raw']).decode('utf-8', errors='ignore')
                row['decoded_response'] = decoded_response
            except Exception:
                row['decoded_response'] = ""
                row['decoding_error_response'] = True
            
            row['source_id'] = int(row['id'])
            del row['id']

            tags = apply_rules(row, loaded_rules)
            row['tags'] = tags
            if tags:
                tagged_count += 1

            # Clean up parsed data before insertion
            if 'request' in row: del row['request']
            if 'response' in row: del row['response']

            result = records_collection.replace_one({'source_id': row['source_id']}, row, upsert=True)
            if result.upserted_id:
                inserted_count += 1
            elif result.modified_count > 0:
                updated_count += 1

        print("\nIngestion Complete.")
        print(f"- Records Processed: {len(records)}")
        print(f"- Records Inserted: {inserted_count}")
        print(f"- Records Updated: {updated_count}")
        print(f"- Records with Tags: {tagged_count}")

        print("\nCreating indexes...")
        records_collection.create_index("tags")
        records_collection.create_index("source_id", unique=True)
        records_collection.create_index("host")
        print("Indexes created.")

    except FileNotFoundError:
        print(f"Error: File not found at {file}")
        raise typer.Exit(code=1)
    except Exception as e:
        print(f"An error occurred: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
