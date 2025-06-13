"""Main FastAPI application for weather service."""

import logging
import time
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import WeatherResponse, ErrorResponse
from .services import WeatherService, StorageService, DatabaseService
from config.settings import settings
from config.logging import setup_logging


# Setup logging
logger = setup_logging()


# Service instances
weather_service: Optional[WeatherService] = None
storage_service: Optional[StorageService] = None
database_service: Optional[DatabaseService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    global weather_service, storage_service, database_service
    
    logger.info("Starting Weather API service...")
    
    # Initialize services
    weather_service = WeatherService()
    storage_service = StorageService()
    database_service = DatabaseService()
    
    # Setup infrastructure
    try:
        await storage_service.ensure_bucket_exists()
        await database_service.ensure_table_exists()
        logger.info("Infrastructure setup completed")
    except Exception as e:
        logger.error(f"Failed to setup infrastructure: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down Weather API service...")
    if weather_service:
        await weather_service.close()


# Create FastAPI app
app = FastAPI(
    title="Weather API Service",
    description="A high-performance weather API service with caching and cloud storage",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_services():
    """Dependency to get service instances."""
    return weather_service, storage_service, database_service


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/weather", response_model=WeatherResponse)
async def get_weather(
    city: str = Query(..., description="City name to get weather for"),
    services = Depends(get_services)
):
    """
    Get current weather data for a specified city.
    
    This endpoint:
    1. Checks for cached data (within last 5 minutes)
    2. If no cache, fetches from OpenWeatherMap API
    3. Stores the response in S3
    4. Logs the event in DynamoDB
    5. Returns the weather data
    
    Args:
        city: Name of the city to get weather for
        
    Returns:
        WeatherResponse with current weather data
        
    Raises:
        HTTPException: If city not found or service error occurs
    """
    start_time = time.time()
    weather_svc, storage_svc, db_svc = services
    
    try:
        logger.info(f"Processing weather request for city: {city}")
        
        # Check for cached data first
        cached_data = await storage_svc.get_cached_weather_data(city)
        
        if cached_data:
            # Calculate cache age
            cache_age = datetime.utcnow() - cached_data.timestamp
            cache_age_minutes = cache_age.total_seconds() / 60
            
            response_time = (time.time() - start_time) * 1000
            
            # Log the cached response event
            try:
                await db_svc.log_weather_event(
                    city=city,
                    s3_path="cached",
                    response_time_ms=response_time,
                    cached=True
                )
            except Exception as e:
                logger.warning(f"Failed to log cached event: {e}")
            
            logger.info(f"Returning cached data for {city} (age: {cache_age_minutes:.1f} minutes)")
            
            return WeatherResponse(
                success=True,
                data=cached_data,
                message=f"Weather data for {city} (cached)",
                cached=True,
                cache_age_minutes=cache_age_minutes
            )
        
        # No valid cache, fetch fresh data
        logger.info(f"No valid cache found, fetching fresh data for {city}")
        
        try:
            weather_data = await weather_svc.get_weather_data(city)
        except ValueError as e:
            # City not found
            response_time = (time.time() - start_time) * 1000
            
            # Log the error event
            try:
                await db_svc.log_weather_event(
                    city=city,
                    s3_path="",
                    response_time_ms=response_time,
                    cached=False,
                    error=str(e)
                )
            except Exception as log_err:
                logger.warning(f"Failed to log error event: {log_err}")
            
            raise HTTPException(status_code=404, detail=str(e))
        
        except Exception as e:
            # Other API errors
            response_time = (time.time() - start_time) * 1000
            
            # Log the error event
            try:
                await db_svc.log_weather_event(
                    city=city,
                    s3_path="",
                    response_time_ms=response_time,
                    cached=False,
                    error=str(e)
                )
            except Exception as log_err:
                logger.warning(f"Failed to log error event: {log_err}")
            
            logger.error(f"Error fetching weather data: {e}")
            raise HTTPException(status_code=503, detail="Weather service temporarily unavailable")
        
        # Store the data in S3
        try:
            s3_path = await storage_svc.store_weather_data(weather_data)
        except Exception as e:
            logger.error(f"Failed to store weather data: {e}")
            s3_path = "storage_failed"
        
        response_time = (time.time() - start_time) * 1000
        
        # Log the successful event
        try:
            await db_svc.log_weather_event(
                city=city,
                s3_path=s3_path,
                response_time_ms=response_time,
                cached=False
            )
        except Exception as e:
            logger.warning(f"Failed to log successful event: {e}")
        
        logger.info(f"Successfully processed weather request for {city} in {response_time:.1f}ms")
        
        return WeatherResponse(
            success=True,
            data=weather_data,
            message=f"Current weather data for {city}",
            cached=False
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error processing weather request for {city}: {e}")
        response_time = (time.time() - start_time) * 1000
        
        # Log the error event
        try:
            await db_svc.log_weather_event(
                city=city,
                s3_path="",
                response_time_ms=response_time,
                cached=False,
                error=str(e)
            )
        except Exception as log_err:
            logger.warning(f"Failed to log error event: {log_err}")
        
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/stats")
async def get_stats(services = Depends(get_services)):
    """Get API usage statistics."""
    try:
        _, storage_svc, db_svc = services
        
        # Get recent events
        events = await db_svc.get_recent_events(limit=100)
        
        # Get recent files
        recent_files = await storage_svc.list_recent_files(hours=24)
        
        # Calculate statistics
        total_requests = len(events)
        cached_requests = sum(1 for event in events if event.cached)
        error_requests = sum(1 for event in events if event.error)
        
        avg_response_time = (
            sum(event.response_time_ms for event in events) / total_requests
            if total_requests > 0 else 0
        )
        
        return {
            "total_requests_24h": total_requests,
            "cached_requests": cached_requests,
            "cache_hit_rate": cached_requests / total_requests if total_requests > 0 else 0,
            "error_requests": error_requests,
            "error_rate": error_requests / total_requests if total_requests > 0 else 0,
            "avg_response_time_ms": round(avg_response_time, 2),
            "files_stored_24h": len(recent_files)
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="Internal server error",
            details={"error": str(exc)}
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
