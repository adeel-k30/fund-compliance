from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
import json

from app.core.config import settings
from app.models.rules import FieldRule
from app.services.rule_engine import RuleEngine
from app.routers.validation import router as validation_router
from app.routers.client import router as client_router

app = FastAPI(title=settings.app_name,
              description="Validates fund data against regulatory requirements",
              version=settings.app_version)

app.include_router(validation_router)
app.include_router(client_router)

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str

class RootResponse(BaseModel):
    message: str
    api_docs: str

@app.on_event("startup")
async def startup_event():
    # Load rules from JSON file
    rules_path = Path("app/data/emt_rules.json")
    raw = json.loads(rules_path.read_text())

    # Convert to list of FieldRule objects
    rules = [FieldRule.model_validate(r) for r in raw]

    # Initialize Rule Engine with loaded rules
    app.state.emt_rules = rules
    app.state.rule_engine = RuleEngine(rules)
    print(f"Loaded {len(rules)} EMT rules")

@app.get("/", tags=["Root"])
async def root() -> RootResponse:
    return RootResponse(
        message="Welcome to the Fund Compliance API. Use /docs for API documentation.",
        api_docs="/docs"
    )

@app.get("/health", tags=["Health"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="OK",
        service=settings.app_name,
        version=settings.app_version
    )