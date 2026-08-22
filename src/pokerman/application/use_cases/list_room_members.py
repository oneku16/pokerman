from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import RoomPlayer


async def list_room_members(uow: UnitOfWork, *, room_id: int) -> list[RoomPlayer]:
    async with uow:
        return await uow.room_players.list_for_room(room_id)
