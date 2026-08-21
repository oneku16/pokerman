import pytest

from pokerman.application.use_cases.close_room import close_room
from pokerman.application.use_cases.reject_buy_in import reject_buy_in
from pokerman.application.use_cases.request_buy_in import request_buy_in
from pokerman.domain.enums import BuyInStatus
from pokerman.domain.errors import (
    InvalidBuyInAmountError,
    NotRoomMemberError,
    RoomClosedError,
    RoomNotFoundError,
)
from tests.application.fakes import FakeUnitOfWork
from tests.application.helpers import add_player, make_room


class TestRequestBuyIn:
    async def test_first_buy_in_must_equal_default_amount(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, default_buy_in_amount=500)
        assert room.id is not None

        result = await request_buy_in(uow, room_id=room.id, player_telegram_id=1, amount=500)

        assert result.buy_in.amount == 500
        assert result.buy_in.status == BuyInStatus.PENDING
        assert result.room.id == room.id
        assert uow.committed is True

    async def test_first_buy_in_rejects_amount_other_than_default(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, default_buy_in_amount=500)
        assert room.id is not None

        with pytest.raises(InvalidBuyInAmountError):
            await request_buy_in(uow, room_id=room.id, player_telegram_id=1, amount=1000)

    async def test_second_buy_in_must_exceed_default_amount(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)

        result = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=600)

        assert result.buy_in.amount == 600

    async def test_second_buy_in_equal_to_default_is_rejected(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)

        with pytest.raises(InvalidBuyInAmountError):
            await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)

    async def test_second_buy_in_below_default_is_rejected(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)

        with pytest.raises(InvalidBuyInAmountError):
            await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=100)

    async def test_rejected_first_buy_in_does_not_count_as_first(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        first = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)
        assert first.buy_in.id is not None
        await reject_buy_in(uow, buy_in_id=first.buy_in.id, admin_telegram_id=1)

        retry = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)

        assert retry.buy_in.amount == 500
        assert retry.buy_in.status == BuyInStatus.PENDING

    async def test_admin_can_buy_in_to_their_own_room(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None

        result = await request_buy_in(uow, room_id=room.id, player_telegram_id=1, amount=500)

        assert result.buy_in.status == BuyInStatus.PENDING

    async def test_non_member_cannot_request_a_buy_in(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, default_buy_in_amount=500)
        assert room.id is not None

        with pytest.raises(NotRoomMemberError):
            await request_buy_in(uow, room_id=room.id, player_telegram_id=99, amount=500)

    async def test_unknown_room_raises_not_found(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(RoomNotFoundError):
            await request_buy_in(uow, room_id=404, player_telegram_id=1, amount=500)

    async def test_cannot_request_on_closed_room(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await close_room(uow, room_id=room.id, admin_telegram_id=1)

        with pytest.raises(RoomClosedError):
            await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)

    async def test_multiple_concurrent_pending_requests_are_allowed(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")

        first = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)
        second = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=600)

        assert first.buy_in.id != second.buy_in.id
        assert first.buy_in.status == BuyInStatus.PENDING
        assert second.buy_in.status == BuyInStatus.PENDING
