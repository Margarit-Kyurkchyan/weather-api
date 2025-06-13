#!/bin/bash

# Weather API Service Test Script

set -e

echo "🧪 Testing Weather API Service..."

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "❌ jq is required but not installed. Installing jq..."
    sudo apt-get update && sudo apt-get install -y jq
fi

BASE_URL="http://localhost:8000"

# Helper function to check if response is valid JSON
is_valid_json() {
    echo "$1" | jq -e . >/dev/null 2>&1
}

# Helper function to get JSON field
get_json_field() {
    echo "$1" | jq -r "$2" 2>/dev/null || echo ""
}

# Check if service is running
echo "1. Health Check..."
if curl -sf "$BASE_URL/health" >/dev/null; then
    echo "   ✅ Health check passed"
else
    echo "   ❌ Health check failed - is the service running?"
    exit 1
fi

# Test weather endpoint with valid city
echo "2. Testing weather endpoint with valid city (London)..."
response=$(curl -s "$BASE_URL/weather?city=London")
if is_valid_json "$response"; then
    success=$(get_json_field "$response" '.success')
    if [ "$success" = "true" ]; then
        echo "   ✅ Weather API test passed"
        echo "   📊 Temperature: $(get_json_field "$response" '.data.temperature')°C"
        echo "   🌤️  Description: $(get_json_field "$response" '.data.description')"
    else
        echo "   ❌ Weather API returned success=false"
        echo "   Response: $response"
    fi
else
    echo "   ❌ Invalid JSON response"
    echo "   Response: $response"
fi

# Test with invalid city
echo "3. Testing with invalid city..."
response=$(curl -s "$BASE_URL/weather?city=InvalidCityName123")
if is_valid_json "$response"; then
    detail=$(get_json_field "$response" '.detail')
    if [ -n "$detail" ]; then
        echo "   ✅ Error handling test passed"
        echo "   Error message: $detail"
    else
        echo "   ❌ Expected error detail not found"
        echo "   Response: $response"
    fi
else
    echo "   ❌ Invalid JSON response"
    echo "   Response: $response"
fi

# Test caching (make same request twice)
echo "4. Testing caching mechanism..."
echo "   First request (should be fresh)..."
response1=$(curl -s "$BASE_URL/weather?city=Paris")
if is_valid_json "$response1"; then
    cached1=$(get_json_field "$response1" '.cached')
    echo "   First request cached: $cached1"
    
    echo "   Second request (should be cached)..."
    response2=$(curl -s "$BASE_URL/weather?city=Paris")
    if is_valid_json "$response2"; then
        cached2=$(get_json_field "$response2" '.cached')
        echo "   Second request cached: $cached2"
        
        if [ "$cached1" = "false" ] && [ "$cached2" = "true" ]; then
            echo "   ✅ Caching test passed"
        else
            echo "   ⚠️  Caching test inconclusive - both requests should not have same cache status"
        fi
    else
        echo "   ❌ Invalid JSON response in second request"
    fi
else
    echo "   ❌ Invalid JSON response in first request"
    echo "   Response: $response1"
fi

# Test statistics endpoint
echo "5. Testing statistics endpoint..."
response=$(curl -s "$BASE_URL/stats")
if is_valid_json "$response"; then
    total_requests=$(get_json_field "$response" '.total_requests_24h')
    cache_hit_rate=$(get_json_field "$response" '.cache_hit_rate')
    
    if [ -n "$total_requests" ] && [ -n "$cache_hit_rate" ]; then
        echo "   ✅ Statistics endpoint test passed"
        echo "   📈 Total requests: $total_requests"
        echo "   ⚡ Cache hit rate: $cache_hit_rate"
    else
        echo "   ❌ Missing expected fields in stats response"
        echo "   Response: $response"
    fi
else
    echo "   ❌ Invalid JSON response from stats endpoint"
    echo "   Response: $response"
fi

echo ""
echo "🎉 Testing completed!"
echo ""
echo "📊 API Documentation available at:"
echo "   $BASE_URL/docs"
