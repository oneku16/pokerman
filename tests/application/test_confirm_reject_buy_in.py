import pytest

from pokerman.application.use_cases.confirm_buy_in import confirm_buy_in
from pokerman.application.use_cases.reject_buy_in import reject_buy_in
from pokerman.application.use_cases.request_buy_in import request_buy_in
from pokerman.domain.enums import BuyInStatus
from pokerman.domain.errors import (
    BuyInNotFoundError,
    InvalidBuyInStateError,
    UnauthorizedActionError,
)
from tests.application.fakes import FakeUnitOfWork
from tests.application.helpers import add_player, make_room


class TestConfirmBuyIn:
    async def test_confirms_a_pending_buy_in(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        requested = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)
        assert requested.buy_in.id is not None

        result = await confirm_buy_in(uow, buy_in_id=requested.buy_in.id, admin_telegram_id=1)

        assert result.buy_in.status == BuyInStatus.CONFIRMED
        assert result.buy_in.decided_by_telegram_id == 1
        assert result.buy_in.decided_at is not None
        assert result.room.id == room.id
        assert result.player_telegram_id == 2

    async def test_non_admin_cannot_confirm(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        requested = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)
        assert requested.buy_in.id is not None

        with pytest.raises(UnauthorizedActionError):
            await confirm_buy_in(uow, buy_in_id=requested.buy_in.id, admin_telegram_id=2)

    async def test_admin_of_a_different_room_cannot_confirm(self) -> None:
        uow = FakeUnitOfWork()
        room_a = await make_room(uow, code="1111", admin_telegram_id=1, name="Room A")
        assert room_a.id is not None
        await add_player(uow, room_a, telegram_id=2, display_name="Azamat")
        requested = await request_buy_in(uow, room_id=room_a.id, player_telegram_id=2, amount=500)
        assert requested.buy_in.id is not None

        await make_room(uow, code="2222", admin_telegram_id=3, name="Room B")

        with pytest.raises(UnauthorizedActionError):
            await confirm_buy_in(uow, buy_in_id=requested.buy_in.id, admin_telegram_id=3)

    async def test_double_confirm_fails(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        requested = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)
        assert requested.buy_in.id is not None
        await confirm_buy_in(uow, buy_in_id=requested.buy_in.id, admin_telegram_id=1)

        with pytest.raises(InvalidBuyInStateError):
            await confirm_buy_in(uow, buy_in_id=requested.buy_in.id, admin_telegram_id=1)

    async def test_unknown_buy_in_raises_not_found(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(BuyInNotFoundError):
            await confirm_buy_in(uow, buy_in_id=404, admin_telegram_id=1)


class TestRejectBuyIn:
    async def test_rejects_a_pending_buy_in(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        requested = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)
        assert requested.buy_in.id is not None

        result = await reject_buy_in(uow, buy_in_id=requested.buy_in.id, admin_telegram_id=1)

        assert result.buy_in.status == BuyInStatus.REJECTED
        assert result.player_telegram_id == 2

    async def test_non_admin_cannot_reject(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        requested = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)
        assert requested.buy_in.id is not None

        with pytest.raises(UnauthorizedActionError):
            await reject_buy_in(uow, buy_in_id=requested.buy_in.id, admin_telegram_id=2)

    async def test_rejected_buy_in_does_not_count_toward_totals_via_confirm(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        requested = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)
        assert requested.buy_in.id is not None
        await reject_buy_in(uow, buy_in_id=requested.buy_in.id, admin_telegram_id=1)

        with pytest.raises(InvalidBuyInStateError):
            await confirm_buy_in(uow, buy_in_id=requested.buy_in.id, admin_telegram_id=1)
