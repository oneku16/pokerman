from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import User
from pokerman.domain.errors import UserNotFoundError


async def set_default_qr(uow: UnitOfWork, *, telegram_id: int, qr_file_id: str) -> User:
    async with uow:
        user = await uow.users.get_by_telegram_id(telegram_id)
        if user is None:
            raise UserNotFoundError(f"user {telegram_id} is not registered")

        user.set_default_qr(qr_file_id)
        await uow.users.save(user)
        await uow.commit()
        return user
