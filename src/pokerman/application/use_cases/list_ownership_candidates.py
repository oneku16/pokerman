from pokerman.application.authorization import ensure_is_admin
from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import User
from pokerman.domain.errors import RoomNotFoundError


async def list_ownership_candidates(
    uow: UnitOfWork, *, room_id: int, admin_telegram_id: int
) -> list[User]:
    async with uow:
        room = await uow.rooms.get_by_id(room_id)
        if room is None:
            raise RoomNotFoundError(f"room {room_id} not found")
        ensure_is_admin(room, admin_telegram_id)
        room.ensure_active()

        members = await uow.room_players.list_for_room(room_id)
        candidates: list[User] = []
        for member in sorted(members, key=lambda m: m.joined_at):
            if member.user_telegram_id == room.admin_telegram_id:
                continue
            user = await uow.users.get_by_telegram_id(member.user_telegram_id)
            if user is not None:
                candidates.append(user)
        return candidates
