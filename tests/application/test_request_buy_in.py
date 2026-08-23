import pytest

from pokerman.application.use_cases.close_room import close_room
from pokerman.application.use_cases.confirm_buy_in import confirm_buy_in
from pokerman.application.use_cases.request_buy_in import request_buy_in
from pokerman.application.use_cases.set_spending_limit import set_spending_limit
from pokerman.domain.enums import BuyInStatus
from pokerman.domain.errors import (
    NotRoomMemberError,
    RoomClosedError,
    RoomNotFoundError,
    SpendingLimitExceededError,
)
from tests.application.fakes import FakeUnitOfWork
from tests.application.helpers import add_player, make_room


class TestRequestBuyIn:
    async def test_accepts_the_room_default_amount(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, default_buy_in_amount=500)
        assert room.id is not None

        result = await request_buy_in(uow, room_id=room.id, player_telegram_id=1, amount=500)

        assert result.buy_in.amount == 500
        assert result.buy_in.status == BuyInStatus.PENDING
        assert result.room.id == room.id
        assert uow.committed is True

    async def test_accepts_any_other_positive_amount(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, default_buy_in_amount=500)
        assert room.id is not None

        result = await request_buy_in(uow, room_id=room.id, player_telegram_id=1, amount=50)

        assert result.buy_in.amount == 50
        assert result.buy_in.status == BuyInStatus.PENDING

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

        first = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=200)
        second = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=200)

        assert first.buy_in.id != second.buy_in.id
        assert first.buy_in.status == BuyInStatus.PENDING
        assert second.buy_in.status == BuyInStatus.PENDING


class TestRequestBuyInSpendingLimit:
    async def test_request_within_limit_is_allowed(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await set_spending_limit(uow, telegram_id=2, limit=500)

        result = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)

        assert result.buy_in.amount == 500

    async def test_request_exceeding_limit_is_blocked(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await set_spending_limit(uow, telegram_id=2, limit=500)

        with pytest.raises(SpendingLimitExceededError) as exc_info:
            await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=600)

        assert exc_info.value.limit == 500
        assert exc_info.value.current_total == 0
        assert exc_info.value.requested_amount == 600

    async def test_confirmed_buy_ins_accumulate_toward_the_limit(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await set_spending_limit(uow, telegram_id=2, limit=500)
        first = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=400)
        assert first.buy_in.id is not None
        await confirm_buy_in(uow, buy_in_id=first.buy_in.id, admin_telegram_id=1)

        with pytest.raises(SpendingLimitExceededError) as exc_info:
            await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=200)

        assert exc_info.value.current_total == 400

    async def test_pending_buy_ins_do_not_count_toward_the_limit(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await set_spending_limit(uow, telegram_id=2, limit=500)
        await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=400)

        result = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=400)

        assert result.buy_in.amount == 400

    async def test_limit_is_per_room_not_lifetime(self) -> None:
        uow = FakeUnitOfWork()
        room_a = await make_room(uow, code="1111", admin_telegram_id=1, name="Room A")
        assert room_a.id is not None
        await add_player(uow, room_a, telegram_id=2, display_name="Azamat")
        await set_spending_limit(uow, telegram_id=2, limit=500)
        spent = await request_buy_in(uow, room_id=room_a.id, player_telegram_id=2, amount=500)
        assert spent.buy_in.id is not None
        await confirm_buy_in(uow, buy_in_id=spent.buy_in.id, admin_telegram_id=1)

        room_b = await make_room(uow, code="2222", admin_telegram_id=3, name="Room B")
        assert room_b.id is not None
        await add_player(uow, room_b, telegram_id=2, display_name="Azamat")

        result = await request_buy_in(uow, room_id=room_b.id, player_telegram_id=2, amount=500)

        assert result.buy_in.amount == 500

    async def test_no_limit_set_means_unlimited(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")

        result = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=100000)

        assert result.buy_in.amount == 100000
