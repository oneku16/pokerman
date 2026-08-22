from datetime import UTC, datetime

from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import RoomPlayer
from pokerman.domain.enums import RoomStatus
from pokerman.domain.errors import NotRoomMemberError, RoomNotClosedError, RoomNotFoundError


async def record_cash_out(
    uow: UnitOfWork, *, room_id: int, player_telegram_id: int, chip_count: int
) -> RoomPlayer:
    async with uow:
        room = await uow.rooms.get_by_id(room_id)
        if room is None:
            raise RoomNotFoundError(f"room {room_id} not found")
        if room.status != RoomStatus.CLOSED:
            raise RoomNotClosedError(f"room {room_id} is not closed yet")

        member = await uow.room_players.get(room_id, player_telegram_id)
        if member is None:
            raise NotRoomMemberError(
                f"user {player_telegram_id} is not a member of room {room_id}"
            )

        member.record_cash_out(chip_count, datetime.now(UTC))
        await uow.room_players.save(member)
        await uow.commit()
        return member
