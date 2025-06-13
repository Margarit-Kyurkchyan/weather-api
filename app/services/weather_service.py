"""Weather service for fetching data from OpenWeatherMap API."""

import logging
from datetime import datetime
from typing import Optional
import httpx

from ..models import WeatherData
from config.settings import settings


logger = logging.getLogger(__name__)


class WeatherService:
    """Service for fetching weather data from OpenWeatherMap API."""
    
    def __init__(self):
        self.api_key = settings.openweather_api_key
        self.base_url = settings.openweather_base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_weather_data(self, city: str) -> Optional[WeatherData]:
        """
        Fetch weather data for a specific city from OpenWeatherMap API.
        
        Args:
            city: The city name to fetch weather data for
            
        Returns:
            WeatherData object if successful, None if failed
            
        Raises:
            httpx.HTTPError: If API request fails
            ValueError: If city name is invalid or API response is malformed
        """
        try:
            url = f"{self.base_url}/weather"
            params = {
                "q": city,
                "appid": self.api_key,
                "units": "metric"
            }
            
            logger.info(f"Fetching weather data for city: {city}")
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse the OpenWeatherMap response
            weather_data = WeatherData(
                city=data["name"],
                country=data["sys"]["country"],
                temperature=data["main"]["temp"],
                feels_like=data["main"]["feels_like"],
                humidity=data["main"]["humidity"],
                pressure=data["main"]["pressure"],
                description=data["weather"][0]["description"],
                wind_speed=data.get("wind", {}).get("speed", 0),
                wind_direction=data.get("wind", {}).get("deg", 0),
                visibility=data.get("visibility", 0),
                clouds=data.get("clouds", {}).get("all", 0),
                timestamp=datetime.utcnow(),
                sunrise=datetime.fromtimestamp(data["sys"]["sunrise"]) if "sunrise" in data["sys"] else None,
                sunset=datetime.fromtimestamp(data["sys"]["sunset"]) if "sunset" in data["sys"] else None,
            )
            
            logger.info(f"Successfully fetched weather data for {city}")
            return weather_data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"City not found: {city}")
                raise ValueError(f"City '{city}' not found")
            else:
                logger.error(f"HTTP error fetching weather data for {city}: {e}")
                raise
                
        except httpx.RequestError as e:
            logger.error(f"Network error fetching weather data for {city}: {e}")
            raise
            
        except KeyError as e:
            logger.error(f"Invalid API response format for {city}: {e}")
            raise ValueError(f"Invalid weather data format received")
            
        except Exception as e:
            logger.error(f"Unexpected error fetching weather data for {city}: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
