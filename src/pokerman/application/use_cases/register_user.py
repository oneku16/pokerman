from pokerman.application.ports import UnitOfWork
from pokerman.application.user_registration import upsert_user
from pokerman.domain.entities import User


async def register_user(
    uow: UnitOfWork, *, telegram_id: int, username: str | None, display_name: str
) -> User:
    async with uow:
        user = await upsert_user(
            uow.users, telegram_id=telegram_id, username=username, display_name=display_name
        )
        await uow.commit()
        return user
