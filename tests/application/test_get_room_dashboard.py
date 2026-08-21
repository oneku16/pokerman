import pytest

from pokerman.application.use_cases.close_room import close_room
from pokerman.application.use_cases.confirm_buy_in import confirm_buy_in
from pokerman.application.use_cases.get_room_dashboard import get_room_dashboard
from pokerman.application.use_cases.reject_buy_in import reject_buy_in
from pokerman.application.use_cases.request_buy_in import request_buy_in
from pokerman.domain.errors import NotRoomMemberError, RoomNotFoundError
from tests.application.fakes import FakeRoomLedgerQuery, FakeUnitOfWork
from tests.application.helpers import add_player, make_room


class TestGetRoomDashboard:
    async def test_only_confirmed_buy_ins_count_toward_totals(self) -> None:
        uow = FakeUnitOfWork()
        ledger = FakeRoomLedgerQuery(uow.db)
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")

        confirmed = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)
        rejected = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=600)
        await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=700)
        assert confirmed.buy_in.id is not None
        assert rejected.buy_in.id is not None
        await confirm_buy_in(uow, buy_in_id=confirmed.buy_in.id, admin_telegram_id=1)
        await reject_buy_in(uow, buy_in_id=rejected.buy_in.id, admin_telegram_id=1)

        dashboard = await get_room_dashboard(
            uow, ledger, room_id=room.id, requesting_telegram_id=1
        )

        azamat_row = next(row for row in dashboard.players if row.user_telegram_id == 2)
        assert azamat_row.confirmed_total == 500
        assert azamat_row.confirmed_count == 1
        assert dashboard.total_confirmed == 500

    async def test_totals_sum_across_all_players(self) -> None:
        uow = FakeUnitOfWork()
        ledger = FakeRoomLedgerQuery(uow.db)
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await add_player(uow, room, telegram_id=3, display_name="Nursultan")

        for telegram_id in (2, 3):
            requested = await request_buy_in(
                uow, room_id=room.id, player_telegram_id=telegram_id, amount=500
            )
            assert requested.buy_in.id is not None
            await confirm_buy_in(uow, buy_in_id=requested.buy_in.id, admin_telegram_id=1)

        dashboard = await get_room_dashboard(
            uow, ledger, room_id=room.id, requesting_telegram_id=1
        )

        assert dashboard.total_confirmed == 1000

    async def test_admin_can_view_dashboard(self) -> None:
        uow = FakeUnitOfWork()
        ledger = FakeRoomLedgerQuery(uow.db)
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None

        dashboard = await get_room_dashboard(
            uow, ledger, room_id=room.id, requesting_telegram_id=1
        )

        assert dashboard.room.id == room.id

    async def test_member_can_view_dashboard(self) -> None:
        uow = FakeUnitOfWork()
        ledger = FakeRoomLedgerQuery(uow.db)
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")

        dashboard = await get_room_dashboard(
            uow, ledger, room_id=room.id, requesting_telegram_id=2
        )

        assert dashboard.room.id == room.id

    async def test_non_member_cannot_view_dashboard(self) -> None:
        uow = FakeUnitOfWork()
        ledger = FakeRoomLedgerQuery(uow.db)
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None

        with pytest.raises(NotRoomMemberError):
            await get_room_dashboard(uow, ledger, room_id=room.id, requesting_telegram_id=99)

    async def test_unknown_room_raises_not_found(self) -> None:
        uow = FakeUnitOfWork()
        ledger = FakeRoomLedgerQuery(uow.db)

        with pytest.raises(RoomNotFoundError):
            await get_room_dashboard(uow, ledger, room_id=404, requesting_telegram_id=1)

    async def test_closed_room_dashboard_still_reflects_final_ledger(self) -> None:
        uow = FakeUnitOfWork()
        ledger = FakeRoomLedgerQuery(uow.db)
        room = await make_room(uow, admin_telegram_id=1, default_buy_in_amount=500)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        requested = await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)
        assert requested.buy_in.id is not None
        await confirm_buy_in(uow, buy_in_id=requested.buy_in.id, admin_telegram_id=1)
        await close_room(uow, room_id=room.id, admin_telegram_id=1)

        dashboard = await get_room_dashboard(
            uow, ledger, room_id=room.id, requesting_telegram_id=2
        )

        assert dashboard.total_confirmed == 500
