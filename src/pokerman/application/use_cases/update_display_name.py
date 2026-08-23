from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import User
from pokerman.domain.errors import UserNotFoundError


async def update_display_name(uow: UnitOfWork, *, telegram_id: int, new_name: str) -> User:
    async with uow:
        user = await uow.users.get_by_telegram_id(telegram_id)
        if user is None:
            raise UserNotFoundError(f"user {telegram_id} is not registered")

        user.rename(new_name)
        await uow.users.save(user)
        await uow.commit()
        return user
