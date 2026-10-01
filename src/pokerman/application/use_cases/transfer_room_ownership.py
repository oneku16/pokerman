from dataclasses import dataclass

from pokerman.application.authorization import ensure_is_admin
from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import BuyIn, PokerRoom, User
from pokerman.domain.errors import NotRoomMemberError, RoomNotFoundError, UserNotFoundError


@dataclass(frozen=True, slots=True)
class PendingBuyInRequest:
    buy_in: BuyIn
    player_display_name: str


@dataclass(frozen=True, slots=True)
class OwnershipTransfer:
    room: PokerRoom
    previous_admin_telegram_id: int
    new_admin: User
    pending_buy_ins: list[PendingBuyInRequest]


async def transfer_room_ownership(
    uow: UnitOfWork, *, room_id: int, admin_telegram_id: int, new_admin_telegram_id: int
) -> OwnershipTransfer:
    async with uow:
        room = await uow.rooms.get_by_id(room_id)
        if room is None:
            raise RoomNotFoundError(f"room {room_id} not found")
        ensure_is_admin(room, admin_telegram_id)

        member = await uow.room_players.get(room_id, new_admin_telegram_id)
        if member is None:
            raise NotRoomMemberError(
                f"user {new_admin_telegram_id} is not a member of room {room_id}"
            )
        new_admin = await uow.users.get_by_telegram_id(new_admin_telegram_id)
        if new_admin is None:
            raise UserNotFoundError(f"user {new_admin_telegram_id} not found")

        room.transfer_ownership(new_admin_telegram_id)
        if new_admin.default_qr_file_id is not None:
            room.set_qr(new_admin.default_qr_file_id)
        await uow.rooms.save(room)

        # Requests still waiting on a decision now belong to the new host.
        pending: list[PendingBuyInRequest] = []
        for buy_in in sorted(
            await uow.buy_ins.list_pending_for_room(room_id), key=lambda b: b.requested_at
        ):
            requester = await uow.room_players.get_by_id(buy_in.room_player_id)
            user = (
                await uow.users.get_by_telegram_id(requester.user_telegram_id)
                if requester is not None
                else None
            )
            name = user.display_name if user is not None else "A player"
            pending.append(PendingBuyInRequest(buy_in=buy_in, player_display_name=name))

        await uow.commit()
        return OwnershipTransfer(
            room=room,
            previous_admin_telegram_id=admin_telegram_id,
            new_admin=new_admin,
            pending_buy_ins=pending,
        )
