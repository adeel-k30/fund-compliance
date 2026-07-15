# All application configuration in one place.
# Values are read from the .env file (or environment variables) at startup.
# Pydantic validates and type-coerces every value, so a missing required field
# (like dev_client_id) will cause the app to fail fast with a clear error.

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "Fund Compliance Platform"
    app_version: str = "0.1.0"
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://funduser:devpassword@localhost:5433/fundcompliance"
    dev_client_id: str
    jwt_secret_key: str = "super-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 30
    redis_url: str = "redis://localhost:6379/0"
    s3_bucket_name: str = "fund-compliance-uploads"
    s3_endpoint_url: str | None = "http://localhost:4566"  # Point at LocalStack locally; set to None in production to use real AWS
    aws_access_key_id: str = "test"  # LocalStack accepts any value
    aws_secret_access_key: str = "test"  # LocalStack accepts any value
    aws_region: str = "us-east-1"


settings = Settings()