"""Tests for the Weather API service."""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models import WeatherData


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def sample_weather_data():
    """Sample weather data for testing."""
    return WeatherData(
        city="London",
        country="GB",
        temperature=15.5,
        feels_like=14.2,
        humidity=78,
        pressure=1013,
        description="partly cloudy",
        wind_speed=3.2,
        wind_direction=220,
        visibility=10000,
        clouds=25,
        timestamp=datetime.utcnow(),
        sunrise=datetime.utcnow(),
        sunset=datetime.utcnow()
    )


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint returns OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestWeatherEndpoint:
    """Test weather endpoint functionality."""
    
    @patch('app.main.weather_service')
    @patch('app.main.storage_service')
    @patch('app.main.database_service')
    def test_weather_endpoint_success(self, mock_db, mock_storage, mock_weather, client, sample_weather_data):
        """Test successful weather data retrieval."""
        # Mock services
        mock_storage.get_cached_weather_data = AsyncMock(return_value=None)
        mock_weather.get_weather_data = AsyncMock(return_value=sample_weather_data)
        mock_storage.store_weather_data = AsyncMock(return_value="s3://test-bucket/test-file.json")
        mock_db.log_weather_event = AsyncMock(return_value="event-123")
        
        response = client.get("/weather?city=London")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["city"] == "London"
        assert data["cached"] is False
    
    @patch('app.main.weather_service')
    @patch('app.main.storage_service')
    @patch('app.main.database_service')
    def test_weather_endpoint_cached(self, mock_db, mock_storage, mock_weather, client, sample_weather_data):
        """Test cached weather data retrieval."""
        # Mock cached data
        mock_storage.get_cached_weather_data = AsyncMock(return_value=sample_weather_data)
        mock_db.log_weather_event = AsyncMock(return_value="event-123")
        
        response = client.get("/weather?city=London")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cached"] is True
        assert "cache_age_minutes" in data
    
    @patch('app.main.weather_service')
    @patch('app.main.storage_service')
    @patch('app.main.database_service')
    def test_weather_endpoint_city_not_found(self, mock_db, mock_storage, mock_weather, client):
        """Test weather endpoint with invalid city."""
        # Mock services
        mock_storage.get_cached_weather_data = AsyncMock(return_value=None)
        mock_weather.get_weather_data = AsyncMock(side_effect=ValueError("City 'InvalidCity' not found"))
        mock_db.log_weather_event = AsyncMock(return_value="event-123")
        
        response = client.get("/weather?city=InvalidCity")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_weather_endpoint_missing_city(self, client):
        """Test weather endpoint without city parameter."""
        response = client.get("/weather")
        assert response.status_code == 422  # Validation error


class TestStatsEndpoint:
    """Test statistics endpoint."""
    
    @patch('app.main.storage_service')
    @patch('app.main.database_service')
    def test_stats_endpoint(self, mock_db, mock_storage, client):
        """Test statistics endpoint returns expected data."""
        # Mock data
        mock_events = [
            type('Event', (), {
                'cached': False,
                'error': None,
                'response_time_ms': 150.0
            })(),
            type('Event', (), {
                'cached': True,
                'error': None,
                'response_time_ms': 50.0
            })(),
        ]
        
        mock_db.get_recent_events = AsyncMock(return_value=mock_events)
        mock_storage.list_recent_files = AsyncMock(return_value=["file1.json", "file2.json"])
        
        response = client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_requests_24h" in data
        assert "cache_hit_rate" in data
        assert "avg_response_time_ms" in data


class TestModels:
    """Test data models."""
    
    def test_weather_data_model(self, sample_weather_data):
        """Test WeatherData model serialization."""
        json_data = sample_weather_data.model_dump_json()
        parsed_data = json.loads(json_data)
        
        assert parsed_data["city"] == "London"
        assert parsed_data["temperature"] == 15.5
        assert "timestamp" in parsed_data
    
    def test_weather_data_model_validation(self):
        """Test WeatherData model validation."""
        with pytest.raises(ValueError):
            WeatherData(
                city="",  # Invalid empty city
                country="GB",
                temperature="invalid",  # Invalid temperature type
                feels_like=14.2,
                humidity=78,
                pressure=1013,
                description="partly cloudy",
                wind_speed=3.2,
                wind_direction=220,
                visibility=10000,
                clouds=25,
                timestamp=datetime.utcnow()
            )


@pytest.mark.asyncio
class TestAsyncServices:
    """Test async service functionality."""
    
    async def test_weather_service_mock(self):
        """Test weather service with mock data."""
        from app.services.weather_service import WeatherService
        
        # This would need actual API key for real testing
        # For now, just test instantiation
        service = WeatherService()
        assert service.base_url == "https://api.openweathermap.org/data/2.5"
        await service.close()


if __name__ == "__main__":
    pytest.main([__file__])
