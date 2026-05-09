from sqlalchemy import select

from app.db.models import User, Client

class UserRepository:
    def __init__(self, session):
        self.session = session

    async def create_user(self, organisation_name: str, email: str, hashed_password: str) -> User:
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
