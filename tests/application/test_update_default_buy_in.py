import pytest

from pokerman.application.use_cases.close_room import close_room
from pokerman.application.use_cases.update_default_buy_in import update_default_buy_in
from pokerman.domain.errors import RoomClosedError, UnauthorizedActionError
from tests.application.fakes import FakeUnitOfWork
from tests.application.helpers import add_player, make_room


class TestUpdateDefaultBuyIn:
    async def test_admin_can_update_amount(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None

        updated = await update_default_buy_in(
            uow, room_id=room.id, admin_telegram_id=1, amount=1000
        )

        assert updated.default_buy_in_amount == 1000

    async def test_non_admin_cannot_update_amount(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")

        with pytest.raises(UnauthorizedActionError):
            await update_default_buy_in(uow, room_id=room.id, admin_telegram_id=2, amount=1000)

    async def test_rejects_non_positive_amount(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None

        with pytest.raises(ValueError, match="positive"):
            await update_default_buy_in(uow, room_id=room.id, admin_telegram_id=1, amount=0)

    async def test_cannot_update_on_closed_room(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await close_room(uow, room_id=room.id, admin_telegram_id=1)

        with pytest.raises(RoomClosedError):
            await update_default_buy_in(uow, room_id=room.id, admin_telegram_id=1, amount=1000)
