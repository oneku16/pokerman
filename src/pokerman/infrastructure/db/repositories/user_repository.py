from sqlalchemy.ext.asyncio import AsyncSession

from pokerman.domain.entities import User
from pokerman.infrastructure.db.mappers import apply_user_to_model, user_to_domain
from pokerman.infrastructure.db.models import UserModel


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        model = await self._session.get(UserModel, telegram_id)
        return user_to_domain(model) if model is not None else None

    async def add(self, user: User) -> User:
        model = UserModel()
        apply_user_to_model(user, model)
        self._session.add(model)
        await self._session.flush()
        return user_to_domain(model)

    async def save(self, user: User) -> None:
        model = await self._session.get(UserModel, user.telegram_id)
        assert model is not None
        apply_user_to_model(user, model)
