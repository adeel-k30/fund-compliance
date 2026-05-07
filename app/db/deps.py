from fastapi import Request

from app.db.session import AsyncSessionLocal
from app.services.rule_engine import RuleEngine

# Dependency for FastAPI routes
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

# Dependency to get the RuleEngine instance from the app state
def get_rule_engine(request: Request) -> RuleEngine:
    return request.app.state.rule_engine