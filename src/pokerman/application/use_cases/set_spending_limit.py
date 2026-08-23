from datetime import UTC, datetime

from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import User
from pokerman.domain.errors import UserNotFoundError


async def set_spending_limit(uow: UnitOfWork, *, telegram_id: int, limit: int) -> User:
    async with uow:
        user = await uow.users.get_by_telegram_id(telegram_id)
        if user is None:
            raise UserNotFoundError(f"user {telegram_id} is not registered")

        user.set_spending_limit(limit, datetime.now(UTC))
        await uow.users.save(user)
        await uow.commit()
        return user
