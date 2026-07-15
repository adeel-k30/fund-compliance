# Database engine and session factory setup.
#
# We need TWO different engines because the API and the Celery worker run differently:
#   - The API is async (FastAPI + asyncpg), so it needs an async engine.
#   - Celery tasks are synchronous, so they use a standard sync engine (psycopg2).
#
# The DATABASE_URL uses "+asyncpg" as its driver — we swap it to "+psycopg2"
# for the sync engine so we don't need a second env variable.

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine

from app.core.config import settings

# Async engine + session for FastAPI route handlers
engine = create_async_engine(settings.database_url, echo=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

Base = declarative_base()  # All ORM models inherit from this

# Sync engine + session for Celery worker tasks
sync_engine = create_engine(
    settings.database_url.replace("+asyncpg", "+psycopg2")
)
SyncSessionLocal = sessionmaker(bind=sync_engine)