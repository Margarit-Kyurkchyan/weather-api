#!/bin/bash

# Weather API Service Stop Script

set -e

echo "🛑 Stopping Weather API Service..."

# Stop and remove containers
#docker compose -f docker-compose.yml -f docker-compose.dev.yml down --remove-orphans
docker compose down --remove-orphans

echo "✅ All services stopped!"
echo ""
echo "🗑️  To also remove volumes (all data will be lost):"
#echo "   docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v"
echo "   docker compose down -v"
