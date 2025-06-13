"""S3 storage service for saving weather data."""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List
import aiobotocore.session
from botocore.exceptions import ClientError

from ..models import WeatherData
from config.settings import settings


logger = logging.getLogger(__name__)


class StorageService:
    """Service for storing and retrieving weather data from S3-compatible storage."""
    
    def __init__(self):
        self.session = aiobotocore.session.get_session()
        self.bucket_name = settings.s3_bucket_name
        
        self.config = {
            'region_name': settings.aws_region,
            'aws_access_key_id': settings.aws_access_key_id,
            'aws_secret_access_key': settings.aws_secret_access_key,
            'endpoint_url': settings.aws_endpoint_url_s3
        }
    
    async def _get_client(self):
        """Get an async S3 client."""
        return self.session.create_client('s3', **self.config)
    
    async def ensure_bucket_exists(self):
        """Ensure the S3 bucket exists, create if it doesn't."""
        try:
            async with await self._get_client() as client:
                try:
                    await client.head_bucket(Bucket=self.bucket_name)
                    logger.info(f"Bucket {self.bucket_name} already exists")
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code == '404':
                        # Bucket doesn't exist, create it
                        await client.create_bucket(Bucket=self.bucket_name)
                        logger.info(f"Created bucket {self.bucket_name}")
                    else:
                        logger.error(f"Error checking bucket existence: {e}")
                        raise
        except Exception as e:
            logger.error(f"Failed to ensure bucket exists: {e}")
            raise
    
    def _generate_file_key(self, city: str, timestamp: datetime) -> str:
        """Generate S3 key for the weather data file."""
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        return f"weather_data/{city.lower().replace(' ', '_')}_{timestamp_str}.json"
    
    async def store_weather_data(self, weather_data: WeatherData) -> str:
        """
        Store weather data as JSON file in S3.
        
        Args:
            weather_data: WeatherData object to store
            
        Returns:
            S3 key/path of the stored file
            
        Raises:
            Exception: If storage operation fails
        """
        try:
            file_key = self._generate_file_key(weather_data.city, weather_data.timestamp)
            
            # Convert to dict - fix for Pydantic v2
            data_dict = weather_data.model_dump(mode='json')
            
            # Convert datetime objects to ISO format strings if they weren't already converted
            for key, value in data_dict.items():
                if isinstance(value, datetime):
                    data_dict[key] = value.isoformat()
            
            json_data = json.dumps(data_dict, indent=2, default=str)
            
            async with await self._get_client() as client:
                await client.put_object(
                    Bucket=self.bucket_name,
                    Key=file_key,
                    Body=json_data.encode('utf-8'),
                    ContentType='application/json',
                    Metadata={
                        'city': weather_data.city,
                        'timestamp': weather_data.timestamp.isoformat(),
                        'cached': 'false'
                    }
                )
            
            s3_path = f"s3://{self.bucket_name}/{file_key}"
            logger.info(f"Stored weather data to {s3_path}")
            return s3_path
            
        except Exception as e:
            logger.error(f"Failed to store weather data for {weather_data.city}: {e}")
            raise
    
    async def get_cached_weather_data(self, city: str) -> Optional[WeatherData]:
        """
        Retrieve cached weather data for a city if it exists and is still valid.
        
        Args:
            city: City name to look for cached data
            
        Returns:
            WeatherData object if valid cache exists, None otherwise
        """
        try:
            cache_cutoff = datetime.utcnow() - timedelta(minutes=settings.cache_expiry_minutes)
            
            async with await self._get_client() as client:
                # List objects with the city prefix
                city_prefix = f"weather_data/{city.lower().replace(' ', '_')}_"
                
                response = await client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=city_prefix
                )
                
                if 'Contents' not in response:
                    logger.debug(f"No cached data found for {city}")
                    return None
                
                # Find the most recent file that's still within cache window
                valid_objects = []
                for obj in response['Contents']:
                    if obj['LastModified'].replace(tzinfo=None) > cache_cutoff:
                        valid_objects.append(obj)
                
                if not valid_objects:
                    logger.debug(f"No valid cached data found for {city}")
                    return None
                
                # Get the most recent valid object
                latest_obj = max(valid_objects, key=lambda x: x['LastModified'])
                
                # Retrieve the object
                obj_response = await client.get_object(
                    Bucket=self.bucket_name,
                    Key=latest_obj['Key']
                )
                
                content = await obj_response['Body'].read()
                weather_data_dict = json.loads(content.decode('utf-8'))
                weather_data = WeatherData(**weather_data_dict)
                
                logger.info(f"Retrieved cached weather data for {city}")
                return weather_data
                
        except Exception as e:
            logger.warning(f"Failed to retrieve cached data for {city}: {e}")
            return None
    
    async def list_recent_files(self, hours: int = 24) -> List[str]:
        """
        List recent weather data files.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of S3 keys for recent files
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            async with await self._get_client() as client:
                response = await client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix="weather_data/"
                )
                
                if 'Contents' not in response:
                    return []
                
                recent_files = [
                    obj['Key'] for obj in response['Contents']
                    if obj['LastModified'].replace(tzinfo=None) > cutoff_time
                ]
                
                return recent_files
                
        except Exception as e:
            logger.error(f"Failed to list recent files: {e}")
            return []
