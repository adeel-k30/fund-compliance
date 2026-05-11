from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

Base = declarative_base()  # base class for our SQL tables models

sync_engine = create_engine(
    settings.database_url.replace("+asyncpg", "+psycopg2")
)
SyncSessionLocal = sessionmaker(bind=sync_engine)