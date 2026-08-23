from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import PokerRoom
from pokerman.domain.enums import RoomStatus


async def get_current_or_last_room(uow: UnitOfWork, *, telegram_id: int) -> PokerRoom | None:
    async with uow:
        rooms = await uow.rooms.list_for_user(telegram_id)
        for room in rooms:
            if room.status == RoomStatus.ACTIVE:
                return room
        for room in rooms:
            if room.status == RoomStatus.CLOSED:
                return room
        return None
