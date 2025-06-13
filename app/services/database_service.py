"""DynamoDB service for logging weather API events."""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import aiobotocore.session
from botocore.exceptions import ClientError
from boto3.dynamodb.types import TypeSerializer
from decimal import Decimal

from ..models import WeatherEvent
from config.settings import settings


logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for logging events to DynamoDB-compatible database."""
    
    def __init__(self):
        self.session = aiobotocore.session.get_session()
        self.table_name = settings.dynamodb_table_name
        
        self.config = {
            'region_name': settings.aws_region,
            'aws_access_key_id': settings.aws_access_key_id,
            'aws_secret_access_key': settings.aws_secret_access_key,
            'endpoint_url': settings.aws_endpoint_url_dynamodb
        }
    
    async def _get_client(self):
        """Get an async DynamoDB client."""
        return self.session.create_client('dynamodb', **self.config)
    
    async def ensure_table_exists(self):
        """Ensure the DynamoDB table exists, create if it doesn't."""
        try:
            async with await self._get_client() as client:
                try:
                    await client.describe_table(TableName=self.table_name)
                    logger.info(f"Table {self.table_name} already exists")
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code == 'ResourceNotFoundException':
                        # Table doesn't exist, create it
                        await client.create_table(
                            TableName=self.table_name,
                            KeySchema=[
                                {
                                    'AttributeName': 'event_id',
                                    'KeyType': 'HASH'
                                }
                            ],
                            AttributeDefinitions=[
                                {
                                    'AttributeName': 'event_id',
                                    'AttributeType': 'S'
                                }
                            ],
                            BillingMode='PAY_PER_REQUEST'
                        )
                        
                        # Wait for table to be active
                        waiter = client.get_waiter('table_exists')
                        await waiter.wait(TableName=self.table_name)
                        
                        logger.info(f"Created table {self.table_name}")
                    else:
                        logger.error(f"Error checking table existence: {e}")
                        raise
        except Exception as e:
            logger.error(f"Failed to ensure table exists: {e}")
            raise
    
    def _serialize_item(self, item: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Serialize Python dict to DynamoDB format."""
        serialized = {}

        for key, value in item.items():
            if value is None:
                continue
                
            if isinstance(value, str):
                serialized[key] = {'S': value}
            elif isinstance(value, bool):
                serialized[key] = {'BOOL': value}
            elif isinstance(value, int):
                serialized[key] = {'N': str(value)}
            elif isinstance(value, float):
                # Fix: Ensure we don't create empty strings for DynamoDB numbers
                decimal_value = Decimal(str(value))
                formatted_value = format(decimal_value, '.6f').rstrip('0').rstrip('.')
                
                # If after stripping we get an empty string, default to '0'
                if not formatted_value or formatted_value == '.':
                    formatted_value = '0'
                
                serialized[key] = {'N': formatted_value}
            elif isinstance(value, datetime):
                serialized[key] = {'S': value.isoformat()}
            else:
                # Fallback to string representation for other types
                serialized[key] = {'S': str(value)}

        return serialized
    
    async def log_weather_event(
        self,
        city: str,
        s3_path: str,
        response_time_ms: float,
        cached: bool = False,
        error: Optional[str] = None
    ) -> str:
        """
        Log a weather API event to DynamoDB.
        
        Args:
            city: City name that was requested
            s3_path: S3 path where data was stored
            response_time_ms: Response time in milliseconds
            cached: Whether the response was served from cache
            error: Error message if any occurred
            
        Returns:
            Event ID of the logged event
            
        Raises:
            Exception: If logging operation fails
        """
        try:
            event_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()
            
            event = WeatherEvent(
                event_id=event_id,
                city=city,
                timestamp=timestamp,
                s3_path=s3_path,
                response_time_ms=response_time_ms,
                cached=cached,
                error=error
            )
            
            # Convert to DynamoDB format using model_dump with proper mode
            item_dict = event.model_dump(mode='json')
            item = self._serialize_item(item_dict)
            
            async with await self._get_client() as client:
                await client.put_item(
                    TableName=self.table_name,
                    Item=item
                )
            
            logger.info(f"Logged weather event {event_id} for city {city}")
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to log weather event for {city}: {e}")
            raise
    
    async def get_event(self, event_id: str) -> Optional[WeatherEvent]:
        """
        Retrieve a weather event by ID.
        
        Args:
            event_id: Event ID to retrieve
            
        Returns:
            WeatherEvent object if found, None otherwise
        """
        try:
            async with await self._get_client() as client:
                response = await client.get_item(
                    TableName=self.table_name,
                    Key={'event_id': {'S': event_id}}
                )
                
                if 'Item' not in response:
                    return None
                
                # Deserialize DynamoDB item
                item = response['Item']
                event_data = {}
                
                for key, value in item.items():
                    if 'S' in value:
                        if key in ['timestamp']:
                            event_data[key] = datetime.fromisoformat(value['S'])
                        else:
                            event_data[key] = value['S']
                    elif 'N' in value:
                        if key == 'response_time_ms':
                            event_data[key] = float(value['N'])
                        else:
                            event_data[key] = int(value['N'])
                    elif 'BOOL' in value:
                        event_data[key] = value['BOOL']
                
                return WeatherEvent(**event_data)
                
        except Exception as e:
            logger.error(f"Failed to retrieve event {event_id}: {e}")
            return None
    
    async def get_recent_events(self, limit: int = 50) -> list:
        """
        Get recent weather events (simple scan for demo purposes).
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        try:
            async with await self._get_client() as client:
                response = await client.scan(
                    TableName=self.table_name,
                    Limit=limit
                )
                
                events = []
                for item in response.get('Items', []):
                    event_data = {}
                    for key, value in item.items():
                        if 'S' in value:
                            if key in ['timestamp']:
                                event_data[key] = datetime.fromisoformat(value['S'])
                            else:
                                event_data[key] = value['S']
                        elif 'N' in value:
                            if key == 'response_time_ms':
                                event_data[key] = float(value['N'])
                            else:
                                event_data[key] = int(value['N'])
                        elif 'BOOL' in value:
                            event_data[key] = value['BOOL']
                    
                    events.append(WeatherEvent(**event_data))
                
                # Sort by timestamp (most recent first)
                events.sort(key=lambda x: x.timestamp, reverse=True)
                return events
                
        except Exception as e:
            logger.error(f"Failed to retrieve recent events: {e}")
            return []
