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


settings = Settings()