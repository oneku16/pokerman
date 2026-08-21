import secrets
from datetime import UTC, datetime

from pokerman.application.ports import RoomCodeGenerator, UnitOfWork
from pokerman.application.user_registration import upsert_user
from pokerman.domain.entities import PokerRoom, RoomPlayer


async def create_room(
    uow: UnitOfWork,
    code_generator: RoomCodeGenerator,
    *,
    admin_telegram_id: int,
    admin_username: str | None,
    admin_display_name: str,
    name: str,
    default_buy_in_amount: int,
    currency: str,
) -> PokerRoom:
    async with uow:
        await upsert_user(
            uow.users,
            telegram_id=admin_telegram_id,
            username=admin_username,
            display_name=admin_display_name,
        )

        code = await code_generator.generate_unique_code()
        now = datetime.now(UTC)
        room = await uow.rooms.add(
            PokerRoom.open(
                name=name,
                code=code,
                deep_link_token=secrets.token_urlsafe(12),
                default_buy_in_amount=default_buy_in_amount,
                currency=currency,
                admin_telegram_id=admin_telegram_id,
                now=now,
            )
        )
        assert room.id is not None

        await uow.room_players.add(
            RoomPlayer.join(room_id=room.id, user_telegram_id=admin_telegram_id, now=now)
        )
        await uow.commit()
        return room
