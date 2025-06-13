"""Data models for the weather API service."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_serializer


class WeatherData(BaseModel):
    """Weather data model from OpenWeatherMap API."""
    
    model_config = ConfigDict(
        # Custom serializers replace json_encoders
        arbitrary_types_allowed=True
    )
    
    city: str
    country: str
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    description: str
    wind_speed: float
    wind_direction: int
    visibility: int
    clouds: int
    timestamp: datetime
    sunrise: Optional[datetime] = None
    sunset: Optional[datetime] = None
    
    @field_serializer('timestamp')
    def serialize_timestamp(self, value: datetime) -> str:
        return value.isoformat()
    
    @field_serializer('sunrise')
    def serialize_sunrise(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None
    
    @field_serializer('sunset')
    def serialize_sunset(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class WeatherResponse(BaseModel):
    """API response model for weather endpoint."""
    
    success: bool
    data: Optional[WeatherData] = None
    message: str
    cached: bool = False
    cache_age_minutes: Optional[float] = None


class WeatherEvent(BaseModel):
    """Event model for DynamoDB logging."""
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )
    
    event_id: str
    city: str
    timestamp: datetime
    s3_path: str
    response_time_ms: float
    cached: bool
    error: Optional[str] = None
    
    @field_serializer('timestamp')
    def serialize_timestamp(self, value: datetime) -> str:
        return value.isoformat()


class ErrorResponse(BaseModel):
    """Error response model."""
    
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
