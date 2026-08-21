from datetime import UTC, datetime

from pokerman.application.authorization import ensure_is_admin
from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import PokerRoom
from pokerman.domain.errors import RoomHasPendingBuyInsError, RoomNotFoundError


async def close_room(uow: UnitOfWork, *, room_id: int, admin_telegram_id: int) -> PokerRoom:
    async with uow:
        room = await uow.rooms.get_by_id(room_id)
        if room is None:
            raise RoomNotFoundError(f"room {room_id} not found")
        ensure_is_admin(room, admin_telegram_id)

        pending = await uow.buy_ins.list_pending_for_room(room_id)
        if pending:
            raise RoomHasPendingBuyInsError([b.id for b in pending if b.id is not None])

        room.close(datetime.now(UTC))
        await uow.rooms.save(room)
        await uow.commit()
        return room
