# All application configuration in one place.
# Values are read from the .env file (or environment variables) at startup.
# Pydantic validates and type-coerces every value, so a missing required field will cause the app to fail fast with a clear error.

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "Fund Compliance Platform"
    app_version: str = "0.1.0"
    app_env: str = "development"

    database_url: str = "postgresql://funduser:devpassword@localhost:5433/fundcompliance"

    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 30

    s3_bucket_name: str = "fund-compliance-uploads"
    s3_endpoint_url: str | None = None  # Unset = real AWS. Set to http://localhost:4566 in .env for LocalStack.
    aws_access_key_id: str = "test"  # LocalStack accepts any value
    aws_secret_access_key: str = "test"  # LocalStack accepts any value
    aws_region: str = "us-east-1"

    # ---------- derived values ----------
    @staticmethod
    def _with_driver(url: str, driver: str) -> str:
        """
        Return the URL with an explicit SQLAlchemy driver.
        Handles the legacy 'postgres://' scheme and replaces any driver
        the platform may already have specified.
        """
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1) # SQLAlchemy dropped support for the shorter form "postgres"
        scheme, _, rest = url.partition("://")
        base = scheme.split("+")[0]  # drop any existing +driver
        return f"{base}+{driver}://{rest}"

    @property
    def async_database_url(self) -> str:
        """For create_async_engine — the FastAPI request path."""
        return self._with_driver(self.database_url, "asyncpg")

    @property
    def sync_database_url(self) -> str:
        """For the Celery worker and Alembic — ordinary sync code."""
        return self._with_driver(self.database_url, "psycopg2")


settings = Settings()