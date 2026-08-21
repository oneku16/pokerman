from datetime import UTC, datetime

from pokerman.application.authorization import ensure_is_admin
from pokerman.application.ports import UnitOfWork
from pokerman.application.use_cases._buy_in_lookup import BuyInDecision, get_buy_in_room_and_member


async def reject_buy_in(
    uow: UnitOfWork, *, buy_in_id: int, admin_telegram_id: int
) -> BuyInDecision:
    async with uow:
        buy_in, room, member = await get_buy_in_room_and_member(uow, buy_in_id)
        ensure_is_admin(room, admin_telegram_id)

        buy_in.reject(decided_by_telegram_id=admin_telegram_id, now=datetime.now(UTC))
        await uow.buy_ins.save(buy_in)
        await uow.commit()
        return BuyInDecision(buy_in=buy_in, room=room, player_telegram_id=member.user_telegram_id)
