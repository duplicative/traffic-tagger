#!/bin/bash
# Quick start script for HTTP Traffic Tagger

set -e

echo "==================================="
echo "HTTP Traffic Tagger - Quick Start"
echo "==================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "✓ .env file created"
else
    echo "✓ .env file already exists"
fi

echo ""
echo "Starting services..."
echo ""

# Start services
docker-compose up -d

echo ""
echo "Waiting for services to be ready..."
sleep 5

# Check service status
echo ""
echo "Service Status:"
docker-compose ps

echo ""
echo "==================================="
echo "✓ Services are running!"
echo "==================================="
echo ""
echo "Access the web UI at: http://localhost:9999"
echo "API is available at: http://localhost:8000"
echo ""
echo "To ingest data, run:"
echo "docker-compose run --rm cli ingest \\"
echo "  --file /data/your_traffic.csv \\"
echo "  --rules /data/rules.yaml \\"
echo "  --mongo-uri \"mongodb://admin:password123@database:27017/\""
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
echo ""
