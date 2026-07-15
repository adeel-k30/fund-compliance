# Client (tenant) lookup endpoint.
# Currently unauthenticated — in production restrict this to admin users or remove it entirely.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.client_repository import ClientRepository
from app.schemas.client import ClientSummary
from app.db.deps import get_db

router = APIRouter(
    prefix="/clients",
    tags=["clients"]
)

@router.get("/{client_id}")
async def get_client(
        client_id: str,
        db: AsyncSession = Depends(get_db)
) -> ClientSummary:
    repo = ClientRepository(db)
    client = await repo.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return ClientSummary.model_validate(client)

