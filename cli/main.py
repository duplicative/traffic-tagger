"""CLI for HTTP Traffic Tagger ingestion."""
import base64
import csv
import os
import sys
from datetime import datetime
from typing import Optional
import typer
import click
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
from shared.rule_engine import RuleEngine


def decode_base64_field(encoded_str: str) -> tuple[str, bool]:
    """
    Decode a base64 encoded string.
    
    Args:
        encoded_str: Base64 encoded string
        
    Returns:
        Tuple of (decoded_string, has_error)
    """
    try:
        decoded_bytes = base64.b64decode(encoded_str)
        decoded_str = decoded_bytes.decode('utf-8')
        return decoded_str, False
    except Exception as e:
        return f"Decoding error: {str(e)}", True


@click.command()
@click.option('--file', required=True, help='Path to the CSV file to ingest.')
@click.option('--rules', required=True, help='Path to the YAML file with tagging rules.')
def ingest(file: str, rules: str):
    """
    Ingest HTTP traffic data from CSV into MongoDB with tagging.
    """
    typer.echo(f"Processing records from {file}...")
    
    # Get MongoDB URI from environment
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    typer.echo(f"Connecting to MongoDB at {mongo_uri}")
    
    # Initialize MongoDB connection
    try:
        client = MongoClient(mongo_uri)
        db = client['http_tagger']
        collection = db['records']
        
        # Create indexes
        collection.create_index([("tags", ASCENDING)])
        collection.create_index([("source_id", ASCENDING)], unique=True)
        collection.create_index([("host", ASCENDING)])
        
    except Exception as e:
        typer.echo(f"Error connecting to MongoDB: {e}", err=True)
        raise typer.Exit(code=1)
    
    # Initialize rule engine
    try:
        rule_engine = RuleEngine(rules)
    except Exception as e:
        typer.echo(f"Error loading rules: {e}", err=True)
        raise typer.Exit(code=1)
    
    # Process CSV file
    records_processed = 0
    records_inserted = 0
    records_updated = 0
    records_with_tags = 0
    
    # Increase CSV field size limit for large base64 encoded fields
    csv.field_size_limit(10 * 1024 * 1024)  # 10 MB
    
    try:
        with open(file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                records_processed += 1
                
                # Decode base64 fields
                decoded_request, request_error = decode_base64_field(row.get('raw', ''))
                decoded_response, response_error = decode_base64_field(row.get('response_raw', ''))
                
                # Apply tagging rules
                tags = []
                if not request_error and not response_error:
                    try:
                        tags = rule_engine.apply_rules(decoded_request, decoded_response)
                    except Exception as e:
                        typer.echo(f"Warning: Error applying rules to record {row.get('id')}: {e}", err=True)
                
                # Build document
                document = {
                    'source_id': int(row.get('id', 0)),
                    'host': row.get('host', ''),
                    'method': row.get('method', ''),
                    'path': row.get('path', ''),
                    'http_version': row.get('http_version', ''),
                    'scheme': row.get('scheme', ''),
                    'authority': row.get('authority', ''),
                    'request_content_length': int(row.get('request_content_length', 0)) if row.get('request_content_length') else 0,
                    'request_timestamp_start': int(row.get('request_timestamp_start', 0)) if row.get('request_timestamp_start') else 0,
                    'request_timestamp_end': int(row.get('request_timestamp_end', 0)) if row.get('request_timestamp_end') else 0,
                    'response_status_code': int(row.get('response_status_code', 0)) if row.get('response_status_code') else 0,
                    'response_reason': row.get('response_reason', ''),
                    'response_content_length': int(row.get('response_content_length', 0)) if row.get('response_content_length') else 0,
                    'response_timestamp_start': int(row.get('response_timestamp_start', 0)) if row.get('response_timestamp_start') else 0,
                    'response_timestamp_end': int(row.get('response_timestamp_end', 0)) if row.get('response_timestamp_end') else 0,
                    'response_created_at': int(row.get('response_created_at', 0)) if row.get('response_created_at') else 0,
                    'decoded_request': decoded_request,
                    'request_decoding_error': request_error,
                    'decoded_response': decoded_response,
                    'response_decoding_error': response_error,
                    'tags': tags,
                    'processed_at': datetime.utcnow().isoformat()
                }
                
                # Insert or update document
                try:
                    collection.replace_one(
                        {'source_id': document['source_id']},
                        document,
                        upsert=True
                    )
                    result = collection.find_one({'source_id': document['source_id']})
                    if result:
                        # Check if it was an insert or update
                        if records_processed == 1:
                            records_inserted += 1
                        else:
                            # Simple heuristic: if document exists, it was updated
                            records_inserted += 1
                except Exception as e:
                    typer.echo(f"Warning: Error inserting/updating record {row.get('id')}: {e}", err=True)
                    continue
                
                if tags:
                    records_with_tags += 1
                
                # Progress indicator
                if records_processed % 100 == 0:
                    typer.echo(f"Processed {records_processed} records...", nl=False)
                    typer.echo("\r", nl=False)
    
    except FileNotFoundError:
        typer.echo(f"Error: File {file} not found", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error processing CSV: {e}", err=True)
        raise typer.Exit(code=1)
    
    # Final summary
    typer.echo("\n")
    typer.echo("Ingestion Complete.")
    typer.echo(f"- Records Processed: {records_processed}")
    typer.echo(f"- Records Inserted/Updated: {records_inserted}")
    typer.echo(f"- Records with Tags: {records_with_tags}")
    
    client.close()


if __name__ == "__main__":
    ingest()
