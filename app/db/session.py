# Database engine and session factory setup.
#
# We need TWO different engines because the API and the Celery worker run differently:
#   - The API is async (FastAPI + asyncpg), so it needs an async engine.
#   - Celery tasks are synchronous, so they use a standard sync engine (psycopg2).
#
# The raw DATABASE_URL has no driver specified — the config properties
# inject the correct driver (+asyncpg or +psycopg2) for each engine.

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine

from app.core.config import settings

# Async engine + session for FastAPI route handlers
engine = create_async_engine(settings.async_database_url, echo=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

Base = declarative_base()  # All ORM models inherit from this

# Sync engine + session for Celery worker tasks
sync_engine = create_engine(settings.sync_database_url)

SyncSessionLocal = sessionmaker(bind=sync_engine)