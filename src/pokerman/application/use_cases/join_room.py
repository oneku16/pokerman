from datetime import UTC, datetime

from pokerman.application.ports import UnitOfWork
from pokerman.application.user_registration import upsert_user
from pokerman.domain.entities import PokerRoom, RoomPlayer
from pokerman.domain.errors import DuplicateMembershipError, RoomNotFoundError
from pokerman.domain.value_objects import RoomCode


async def join_room_by_code(
    uow: UnitOfWork,
    *,
    code: str,
    telegram_id: int,
    username: str | None,
    display_name: str,
) -> PokerRoom:
    async with uow:
        room = await uow.rooms.get_by_code(RoomCode(code))
        if room is None:
            raise RoomNotFoundError(f"no active room with code {code}")
        return await _join(uow, room, telegram_id, username, display_name)


async def join_room_by_deep_link(
    uow: UnitOfWork,
    *,
    token: str,
    telegram_id: int,
    username: str | None,
    display_name: str,
) -> PokerRoom:
    async with uow:
        room = await uow.rooms.get_by_deep_link_token(token)
        if room is None:
            raise RoomNotFoundError(f"room not found for token {token}")
        return await _join(uow, room, telegram_id, username, display_name)


async def _join(
    uow: UnitOfWork,
    room: PokerRoom,
    telegram_id: int,
    username: str | None,
    display_name: str,
) -> PokerRoom:
    room.ensure_active()
    assert room.id is not None

    await upsert_user(
        uow.users, telegram_id=telegram_id, username=username, display_name=display_name
    )

    existing = await uow.room_players.get(room.id, telegram_id)
    if existing is not None:
        raise DuplicateMembershipError(f"user {telegram_id} already joined room {room.id}")

    await uow.room_players.add(
        RoomPlayer.join(room_id=room.id, user_telegram_id=telegram_id, now=datetime.now(UTC))
    )
    await uow.commit()
    return room
