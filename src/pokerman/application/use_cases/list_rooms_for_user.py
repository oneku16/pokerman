from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import PokerRoom


async def list_rooms_for_user(
    uow: UnitOfWork, *, telegram_id: int, limit: int | None = None
) -> list[PokerRoom]:
    async with uow:
        return await uow.rooms.list_for_user(telegram_id, limit=limit)
