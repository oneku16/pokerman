from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import PokerRoom
from pokerman.domain.errors import RoomNotFoundError


async def get_room(uow: UnitOfWork, *, room_id: int) -> PokerRoom:
    async with uow:
        room = await uow.rooms.get_by_id(room_id)
        if room is None:
            raise RoomNotFoundError(f"room {room_id} not found")
        return room
