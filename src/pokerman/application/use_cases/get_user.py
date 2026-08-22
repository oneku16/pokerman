from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import User


async def get_user(uow: UnitOfWork, *, telegram_id: int) -> User | None:
    async with uow:
        return await uow.users.get_by_telegram_id(telegram_id)
