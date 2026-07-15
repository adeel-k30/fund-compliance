# Data access layer for the Client (tenant) table.
# Clients are created automatically during user registration (see UserRepository),
# but this repository handles direct lookups by ID (e.g. for the /clients endpoint).

from sqlalchemy import select

from app.db.models import Client

class ClientRepository:
    def __init__(self, session):
        self.session = session

    async def create_client(self, name: str) -> Client:
        new_client = Client(name=name)
        self.session.add(new_client)
        await self.session.commit()
        await self.session.refresh(new_client)
        return new_client

    async def get_client_by_id(self, client_id: str) -> Client | None:
        result = await self.session.execute(select(Client).where(Client.id == client_id))
        return result.scalar_one_or_none()