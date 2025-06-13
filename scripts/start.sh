#!/bin/bash

# Weather API Service Startup Script

set -e

echo "🌤️  Starting Weather API Service..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example"
    cp .env.example .env
    echo "📝 Please edit .env file with your OpenWeatherMap API key"
    echo "   You can get one free at: https://openweathermap.org/api"
    exit 1
fi

# Check if OpenWeatherMap API key is set
if grep -q "your_openweather_api_key_here" .env; then
    echo "❌ Please set your OpenWeatherMap API key in .env file"
    echo "   You can get one free at: https://openweathermap.org/api"
    exit 1
fi

# Source environment variables
export $(cat .env | grep -v '^#' | xargs)

# Start services
echo "🚀 Starting all services with docker-compose..."
# docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
docker compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check MinIO
echo "   - MinIO (S3-compatible storage)..."
until curl -f http://localhost:9000/minio/health/live >/dev/null 2>&1; do
    echo "     Waiting for MinIO..."
    sleep 2
done
echo "   ✅ MinIO is ready"

# Check DynamoDB Local
echo "   - DynamoDB Local..."
MAX_RETRIES=15
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8002/shell/ >/dev/null 2>&1 || \
       curl -s http://localhost:8002 >/dev/null 2>&1; then
        echo "   ✅ DynamoDB Local is ready"
        break
    fi
    echo "     Waiting for DynamoDB Local... (Attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT + 1))
    
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "   ⚠️  DynamoDB Local is taking longer than expected to start"
        echo "   ℹ️  Trying to continue anyway..."
        break
    fi
done

# Check Weather API
echo "   - Weather API..."
until curl -f http://localhost:8000/health >/dev/null 2>&1; do
    echo "     Waiting for Weather API..."
    sleep 2
done
echo "   ✅ Weather API is ready"

echo ""
echo "🎉 All services are running!"
echo ""
echo "📍 Service URLs:"
echo "   🌤️  Weather API:        http://localhost:8000"
echo "   📚 API Documentation:   http://localhost:8000/docs"
echo "   🗄️  MinIO Console:       http://localhost:9001 (minioadmin/minioadmin)"
echo "   💾 DynamoDB Admin:      http://localhost:8001"
echo ""
echo "🧪 Test the API:"
echo "   curl 'http://localhost:8000/weather?city=London'"
echo ""
echo "📊 View statistics:"
echo "   curl 'http://localhost:8000/stats'"
echo ""
echo "🛑 To stop all services:"
echo "   ./scripts/stop.sh"
