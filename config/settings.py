"""Application configuration settings."""

from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False
    )
    
    # OpenWeatherMap API Configuration
    openweather_api_key: str = Field(..., alias="OPENWEATHER_API_KEY", description="OpenWeatherMap API key")
    openweather_base_url: str = Field(
        default="https://api.openweathermap.org/data/2.5",
        alias="OPENWEATHER_BASE_URL",
        description="OpenWeatherMap API base URL"
    )
    
    # AWS Configuration
    aws_access_key_id: str = Field(default="minioadmin", alias="AWS_ACCESS_KEY_ID", description="AWS access key ID")
    aws_secret_access_key: str = Field(default="minioadmin", alias="AWS_SECRET_ACCESS_KEY", description="AWS secret access key")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION", description="AWS region")
    aws_endpoint_url_s3: str = Field(default="http://localhost:9000", alias="AWS_ENDPOINT_URL_S3", description="S3 endpoint URL")
    aws_endpoint_url_dynamodb: str = Field(default="http://localhost:8000", alias="AWS_ENDPOINT_URL_DYNAMODB", description="DynamoDB endpoint URL")
    
    # S3 Configuration
    s3_bucket_name: str = Field(default="weather-data-bucket", alias="S3_BUCKET_NAME", description="S3 bucket name")
    
    # DynamoDB Configuration
    dynamodb_table_name: str = Field(default="weather-events", alias="DYNAMODB_TABLE_NAME", description="DynamoDB table name")
    
    # Cache Configuration
    cache_expiry_minutes: int = Field(default=5, alias="CACHE_EXPIRY_MINUTES", description="Cache expiry in minutes")
    
    # Application Configuration
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST", description="Application host")
    app_port: int = Field(default=8000, alias="APP_PORT", description="Application port")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL", description="Log level")


# Global settings instance
settings = Settings()
