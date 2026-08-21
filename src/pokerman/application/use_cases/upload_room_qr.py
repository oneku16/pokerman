from pokerman.application.authorization import ensure_is_admin
from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import PokerRoom
from pokerman.domain.errors import RoomNotFoundError


async def upload_room_qr(
    uow: UnitOfWork, *, room_id: int, admin_telegram_id: int, qr_file_id: str
) -> PokerRoom:
    async with uow:
        room = await uow.rooms.get_by_id(room_id)
        if room is None:
            raise RoomNotFoundError(f"room {room_id} not found")
        ensure_is_admin(room, admin_telegram_id)

        room.set_qr(qr_file_id)
        await uow.rooms.save(room)
        await uow.commit()
        return room
