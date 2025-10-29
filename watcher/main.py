"""File watcher service for hot reload of rules and CSV data files."""
import os
import time
import csv
import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Set, Dict, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from pymongo import MongoClient, ASCENDING
from shared.rule_engine import RuleEngine
from shared.http_parser import HTTPParser


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataWatcherHandler(FileSystemEventHandler):
    """Handles file system events for rules and CSV files."""
    
    def __init__(self, data_dir: str, mongo_uri: str, debounce_seconds: int = 5):
        """
        Initialize the watcher handler.
        
        Args:
            data_dir: Path to the data directory to watch
            mongo_uri: MongoDB connection string
            debounce_seconds: Seconds to wait before processing after last change
        """
        self.data_dir = Path(data_dir)
        self.mongo_uri = mongo_uri
        self.debounce_seconds = debounce_seconds
        
        # Track pending changes
        self.pending_rules_reload = False
        self.pending_csv_files: Set[str] = set()
        self.last_change_time = 0
        
        # Track processed CSV files to avoid duplicates
        self.processed_csv_files: Set[str] = self._load_processed_files()
        
        # MongoDB connection
        self.client = None
        self.db = None
        self.collection = None
        self._connect_mongodb()
        
        # Current rules file path
        self.rules_file = self.data_dir / "rules.yaml"
        
        logger.info(f"Watcher initialized. Monitoring: {self.data_dir}")
        logger.info(f"Previously processed CSV files: {len(self.processed_csv_files)}")
    
    def _connect_mongodb(self):
        """Establish MongoDB connection."""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client['http_tagger']
            self.collection = self.db['records']
            
            # Create indexes if they don't exist
            self.collection.create_index([("tags", ASCENDING)])
            self.collection.create_index([("source_id", ASCENDING)], unique=True)
            self.collection.create_index([("host", ASCENDING)])
            
            logger.info("MongoDB connection established")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    def _load_processed_files(self) -> Set[str]:
        """Load list of previously processed CSV files from MongoDB metadata."""
        try:
            client = MongoClient(self.mongo_uri)
            db = client['http_tagger']
            metadata_collection = db['watcher_metadata']
            
            doc = metadata_collection.find_one({'_id': 'processed_files'})
            if doc and 'files' in doc:
                return set(doc['files'])
            return set()
        except Exception as e:
            logger.warning(f"Could not load processed files list: {e}")
            return set()
        finally:
            if client:
                client.close()
    
    def _save_processed_files(self):
        """Save list of processed CSV files to MongoDB metadata."""
        try:
            metadata_collection = self.db['watcher_metadata']
            metadata_collection.replace_one(
                {'_id': 'processed_files'},
                {
                    '_id': 'processed_files',
                    'files': list(self.processed_csv_files),
                    'last_updated': datetime.utcnow().isoformat()
                },
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to save processed files list: {e}")
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Check if it's the rules file
        if file_path.name == "rules.yaml" or file_path.name == "rules.yml":
            logger.info(f"Detected rules file change: {file_path.name}")
            self.pending_rules_reload = True
            self.last_change_time = time.time()
    
    def on_created(self, event: FileSystemEvent):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Check if it's a new CSV file
        if file_path.suffix.lower() == '.csv':
            filename = file_path.name
            
            # Skip if already processed
            if filename in self.processed_csv_files:
                logger.info(f"CSV file already processed, skipping: {filename}")
                return
            
            logger.info(f"Detected new CSV file: {filename}")
            self.pending_csv_files.add(str(file_path))
            self.last_change_time = time.time()
    
    def process_pending_changes(self):
        """Process any pending changes after debounce period."""
        if self.last_change_time == 0:
            return
        
        # Check if debounce period has elapsed
        elapsed = time.time() - self.last_change_time
        if elapsed < self.debounce_seconds:
            return
        
        # Process rules reload
        if self.pending_rules_reload:
            self._reload_rules()
            self.pending_rules_reload = False
        
        # Process new CSV files
        if self.pending_csv_files:
            for csv_file in list(self.pending_csv_files):
                self._ingest_csv_file(csv_file)
            self.pending_csv_files.clear()
        
        # Reset change time
        self.last_change_time = 0
    
    def _reload_rules(self):
        """Reload rules and re-tag all existing records."""
        logger.info("=" * 60)
        logger.info("RULES RELOAD INITIATED")
        logger.info("=" * 60)
        
        try:
            # Check if rules file exists
            if not self.rules_file.exists():
                logger.error(f"Rules file not found: {self.rules_file}")
                return
            
            # Load new rules
            logger.info(f"Loading rules from: {self.rules_file}")
            rule_engine = RuleEngine(str(self.rules_file))
            logger.info(f"Loaded {len(rule_engine.rules)} rules")
            
            # Get all records from MongoDB
            total_records = self.collection.count_documents({})
            logger.info(f"Re-tagging {total_records} existing records...")
            
            records_updated = 0
            records_with_tags = 0
            
            # Process in batches
            batch_size = 100
            for skip in range(0, total_records, batch_size):
                records = self.collection.find({}).skip(skip).limit(batch_size)
                
                for record in records:
                    try:
                        # Re-apply rules
                        tags = []
                        if not record.get('request_decoding_error') and not record.get('response_decoding_error'):
                            decoded_request = record.get('decoded_request', '')
                            decoded_response = record.get('decoded_response', '')
                            tags = rule_engine.apply_rules(decoded_request, decoded_response)
                        
                        # Update record with new tags
                        self.collection.update_one(
                            {'_id': record['_id']},
                            {
                                '$set': {
                                    'tags': tags,
                                    'tags_updated_at': datetime.utcnow().isoformat()
                                }
                            }
                        )
                        
                        records_updated += 1
                        if tags:
                            records_with_tags += 1
                        
                    except Exception as e:
                        logger.error(f"Error re-tagging record {record.get('source_id')}: {e}")
                
                # Progress update
                if (skip + batch_size) % 1000 == 0:
                    logger.info(f"Progress: {skip + batch_size}/{total_records} records processed")
            
            logger.info("=" * 60)
            logger.info("RULES RELOAD COMPLETE")
            logger.info(f"- Records Updated: {records_updated}")
            logger.info(f"- Records with Tags: {records_with_tags}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Failed to reload rules: {e}", exc_info=True)
    
    def _ingest_csv_file(self, csv_file_path: str):
        """Ingest a new CSV file."""
        logger.info("=" * 60)
        logger.info(f"CSV INGESTION INITIATED: {Path(csv_file_path).name}")
        logger.info("=" * 60)
        
        try:
            # Check if rules file exists
            if not self.rules_file.exists():
                logger.error(f"Rules file not found: {self.rules_file}")
                return
            
            # Load rules
            rule_engine = RuleEngine(str(self.rules_file))
            logger.info(f"Loaded {len(rule_engine.rules)} rules")
            
            # Process CSV
            records_processed = 0
            records_inserted = 0
            records_with_tags = 0
            
            # Increase CSV field size limit
            csv.field_size_limit(10 * 1024 * 1024)  # 10 MB
            
            with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    records_processed += 1
                    
                    # Decode base64 fields
                    decoded_request, request_error = self._decode_base64_field(row.get('raw', ''))
                    decoded_response, response_error = self._decode_base64_field(row.get('response_raw', ''))
                    
                    # Apply tagging rules
                    tags = []
                    if not request_error and not response_error:
                        try:
                            tags = rule_engine.apply_rules(decoded_request, decoded_response)
                        except Exception as e:
                            logger.warning(f"Error applying rules to record {row.get('id')}: {e}")
                    
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
                        'processed_at': datetime.utcnow().isoformat(),
                        'source_file': Path(csv_file_path).name
                    }
                    
                    # Insert or update document
                    try:
                        self.collection.replace_one(
                            {'source_id': document['source_id']},
                            document,
                            upsert=True
                        )
                        records_inserted += 1
                    except Exception as e:
                        logger.warning(f"Error inserting/updating record {row.get('id')}: {e}")
                        continue
                    
                    if tags:
                        records_with_tags += 1
                    
                    # Progress indicator
                    if records_processed % 100 == 0:
                        logger.info(f"Progress: {records_processed} records processed...")
            
            # Mark file as processed
            filename = Path(csv_file_path).name
            self.processed_csv_files.add(filename)
            self._save_processed_files()
            
            logger.info("=" * 60)
            logger.info("CSV INGESTION COMPLETE")
            logger.info(f"- File: {filename}")
            logger.info(f"- Records Processed: {records_processed}")
            logger.info(f"- Records Inserted/Updated: {records_inserted}")
            logger.info(f"- Records with Tags: {records_with_tags}")
            logger.info("=" * 60)
            
        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_file_path}")
        except Exception as e:
            logger.error(f"Failed to ingest CSV file: {e}", exc_info=True)
    
    def _decode_base64_field(self, encoded_str: str) -> tuple:
        """Decode a base64 encoded string."""
        try:
            decoded_bytes = base64.b64decode(encoded_str)
            decoded_str = decoded_bytes.decode('utf-8')
            return decoded_str, False
        except Exception as e:
            return f"Decoding error: {str(e)}", True


def main():
    """Main entry point for the watcher service."""
    logger.info("Starting Traffic Tagger Watcher Service")
    
    # Get configuration from environment
    data_dir = os.getenv('DATA_DIR', '/data')
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:password123@database:27017/')
    debounce_seconds = int(os.getenv('DEBOUNCE_SECONDS', '5'))
    
    logger.info(f"Configuration:")
    logger.info(f"  Data Directory: {data_dir}")
    logger.info(f"  MongoDB URI: {mongo_uri.split('@')[1] if '@' in mongo_uri else mongo_uri}")
    logger.info(f"  Debounce Period: {debounce_seconds} seconds")
    
    # Create event handler and observer
    event_handler = DataWatcherHandler(data_dir, mongo_uri, debounce_seconds)
    observer = Observer()
    observer.schedule(event_handler, data_dir, recursive=False)
    
    # Start observer
    observer.start()
    logger.info("File system observer started. Watching for changes...")
    
    try:
        while True:
            time.sleep(1)
            # Check for pending changes to process
            event_handler.process_pending_changes()
    except KeyboardInterrupt:
        logger.info("Shutdown signal received")
        observer.stop()
    
    observer.join()
    
    # Close MongoDB connection
    if event_handler.client:
        event_handler.client.close()
    
    logger.info("Watcher service stopped")


if __name__ == "__main__":
    main()
