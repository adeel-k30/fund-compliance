# Data access layer for User (and Client, since they're created together).
# The repository pattern keeps SQL queries out of route handlers and makes
# the code easier to test

from sqlalchemy import select

from app.db.models import User, Client

class UserRepository:
    def __init__(self, session):
        self.session = session

    async def create_user(self, organisation_name: str, email: str, hashed_password: str) -> User:
        # Registration creates a Client (tenant) AND a User in one transaction.
        # flush() sends the INSERT to Postgres without committing, so we get back
        # the generated client.id to use as the foreign key on the new User.
        client = Client(name=organisation_name)
        self.session.add(client)
        await self.session.flush()  # ensures client.id is available before creating user

        new_user = User(email=email, hashed_password=hashed_password, client_id=client.id)
        self.session.add(new_user)

        await self.session.commit()
        await self.session.refresh(new_user)
        return new_user

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
