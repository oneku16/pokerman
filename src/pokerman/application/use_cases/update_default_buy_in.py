from pokerman.application.authorization import ensure_is_admin
from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import PokerRoom
from pokerman.domain.errors import RoomNotFoundError


async def update_default_buy_in(
    uow: UnitOfWork, *, room_id: int, admin_telegram_id: int, amount: int
) -> PokerRoom:
    async with uow:
        room = await uow.rooms.get_by_id(room_id)
        if room is None:
            raise RoomNotFoundError(f"room {room_id} not found")
        ensure_is_admin(room, admin_telegram_id)

        room.update_default_buy_in(amount)
        await uow.rooms.save(room)
        await uow.commit()
        return room
