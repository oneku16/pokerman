from pokerman.application.use_cases.create_room import create_room
from pokerman.application.use_cases.join_room import join_room_by_code
from pokerman.domain.entities import PokerRoom
from tests.application.fakes import FakeRoomCodeGenerator, FakeUnitOfWork


async def make_room(
    uow: FakeUnitOfWork,
    *,
    code: str = "4821",
    admin_telegram_id: int = 1,
    admin_display_name: str = "Elnazar",
    default_buy_in_amount: int = 500,
    currency: str = "KGS",
    name: str = "Poker Night #24",
) -> PokerRoom:
    codes = FakeRoomCodeGenerator(uow.db, codes=[code])
    return await create_room(
        uow,
        codes,
        admin_telegram_id=admin_telegram_id,
        admin_username=None,
        admin_display_name=admin_display_name,
        name=name,
        default_buy_in_amount=default_buy_in_amount,
        currency=currency,
    )


async def add_player(
    uow: FakeUnitOfWork, room: PokerRoom, telegram_id: int, display_name: str
) -> None:
    await join_room_by_code(
        uow,
        code=str(room.code),
        telegram_id=telegram_id,
        username=None,
        display_name=display_name,
    )
