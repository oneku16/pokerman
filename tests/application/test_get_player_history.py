import pytest

from pokerman.application.use_cases.confirm_buy_in import confirm_buy_in
from pokerman.application.use_cases.get_player_history import get_player_history
from pokerman.application.use_cases.reject_buy_in import reject_buy_in
from pokerman.application.use_cases.request_buy_in import request_buy_in
from pokerman.domain.enums import BuyInStatus
from pokerman.domain.errors import NotRoomMemberError, UnauthorizedActionError
from tests.application.fakes import FakeUnitOfWork
from tests.application.helpers import add_player, make_room


class TestGetPlayerHistory:
    async def test_player_can_view_own_history(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        first = await request_buy_in(uow, room_id=room.id, player_telegram_id=2)
        second = await request_buy_in(uow, room_id=room.id, player_telegram_id=2)
        assert first.buy_in.id is not None
        assert second.buy_in.id is not None
        await confirm_buy_in(uow, buy_in_id=first.buy_in.id, admin_telegram_id=1)
        await confirm_buy_in(uow, buy_in_id=second.buy_in.id, admin_telegram_id=1)

        history = await get_player_history(
            uow, room_id=room.id, target_telegram_id=2, requesting_telegram_id=2
        )

        assert len(history.buy_ins) == 2
        assert history.confirmed_total == 1000
        assert all(b.status == BuyInStatus.CONFIRMED for b in history.buy_ins)

    async def test_history_includes_all_statuses_but_totals_only_confirmed(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        confirmed = await request_buy_in(uow, room_id=room.id, player_telegram_id=2)
        rejected = await request_buy_in(uow, room_id=room.id, player_telegram_id=2)
        await request_buy_in(uow, room_id=room.id, player_telegram_id=2)
        assert confirmed.buy_in.id is not None
        assert rejected.buy_in.id is not None
        await confirm_buy_in(uow, buy_in_id=confirmed.buy_in.id, admin_telegram_id=1)
        await reject_buy_in(uow, buy_in_id=rejected.buy_in.id, admin_telegram_id=1)

        history = await get_player_history(
            uow, room_id=room.id, target_telegram_id=2, requesting_telegram_id=2
        )

        assert len(history.buy_ins) == 3
        assert history.confirmed_total == 500

    async def test_admin_can_view_any_players_history(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")

        history = await get_player_history(
            uow, room_id=room.id, target_telegram_id=2, requesting_telegram_id=1
        )

        assert history.buy_ins == []

    async def test_player_cannot_view_another_players_history(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await add_player(uow, room, telegram_id=3, display_name="Nursultan")

        with pytest.raises(UnauthorizedActionError):
            await get_player_history(
                uow, room_id=room.id, target_telegram_id=2, requesting_telegram_id=3
            )

    async def test_non_member_target_raises_not_room_member(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None

        with pytest.raises(NotRoomMemberError):
            await get_player_history(
                uow, room_id=room.id, target_telegram_id=99, requesting_telegram_id=1
            )
