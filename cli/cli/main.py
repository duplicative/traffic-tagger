import typer
import csv
import base64
from pymongo import MongoClient
from tqdm import tqdm
import yaml

app = typer.Typer()

@app.command()
def ingest(
    file: str = typer.Option(..., "--file", help="Path to the CSV file to ingest."),
    rules: str = typer.Option(..., "--rules", help="Path to the YAML file with tagging rules."),
    mongo_uri: str = typer.Option(..., "--mongo-uri", help="MongoDB connection string."),
):
    """
    Ingests HTTP traffic data from a CSV file, processes it, and stores it in a MongoDB database.
    """
    print(f"Ingesting file: {file}")
    print(f"Using rules: {rules}")
    print(f"Connecting to mongo: {mongo_uri}")

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

        for row in tqdm(records, desc="Processing records"):
            try:
                decoded_request = base64.b64decode(row['raw']).decode('utf-8')
                row['decoded_request'] = decoded_request
            except Exception as e:
                row['decoded_request'] = ""
                row['decoding_error_request'] = True

            try:
                decoded_response = base64.b64decode(row['response_raw']).decode('utf-8')
                row['decoded_response'] = decoded_response
            except Exception as e:
                row['decoded_response'] = ""
                row['decoding_error_response'] = True
            
            row['source_id'] = int(row['id'])
            del row['id']

            records_collection.replace_one({'source_id': row['source_id']}, row, upsert=True)

        print("\nIngestion Complete.")
        print(f"- Records Processed: {len(records)}")

    except FileNotFoundError:
        print(f"Error: File not found at {file}")
        raise typer.Exit(code=1)
    except Exception as e:
        print(f"An error occurred: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
