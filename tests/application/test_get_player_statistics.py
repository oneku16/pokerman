from pokerman.application.use_cases.close_room import close_room
from pokerman.application.use_cases.confirm_buy_in import confirm_buy_in
from pokerman.application.use_cases.get_player_statistics import get_player_statistics
from pokerman.application.use_cases.record_cash_out import record_cash_out
from pokerman.application.use_cases.request_buy_in import request_buy_in
from tests.application.fakes import FakePlayerStatisticsQuery, FakeUnitOfWork
from tests.application.helpers import add_player, make_room


class TestGetPlayerStatistics:
    async def test_zero_stats_for_unknown_player(self) -> None:
        uow = FakeUnitOfWork()
        stats_query = FakePlayerStatisticsQuery(uow.db)

        stats = await get_player_statistics(stats_query, telegram_id=999)

        assert stats.games_played == 0
        assert stats.total_spent == 0
        assert stats.total_buy_in_count == 0
        assert stats.total_cashed_out == 0
        assert stats.net_result == 0

    async def test_active_room_membership_does_not_count_as_games_played(self) -> None:
        uow = FakeUnitOfWork()
        stats_query = FakePlayerStatisticsQuery(uow.db)
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")

        stats = await get_player_statistics(stats_query, telegram_id=2)

        assert stats.games_played == 0

    async def test_aggregates_across_closed_rooms(self) -> None:
        uow = FakeUnitOfWork()
        stats_query = FakePlayerStatisticsQuery(uow.db)

        room_a = await make_room(uow, code="1111", admin_telegram_id=1, name="Room A")
        assert room_a.id is not None
        await add_player(uow, room_a, telegram_id=2, display_name="Azamat")
        buy_in_a = await request_buy_in(uow, room_id=room_a.id, player_telegram_id=2, amount=500)
        assert buy_in_a.buy_in.id is not None
        await confirm_buy_in(uow, buy_in_id=buy_in_a.buy_in.id, admin_telegram_id=1)
        await close_room(uow, room_id=room_a.id, admin_telegram_id=1)
        await record_cash_out(uow, room_id=room_a.id, player_telegram_id=2, chip_count=800)

        room_b = await make_room(uow, code="2222", admin_telegram_id=3, name="Room B")
        assert room_b.id is not None
        await add_player(uow, room_b, telegram_id=2, display_name="Azamat")
        buy_in_b = await request_buy_in(uow, room_id=room_b.id, player_telegram_id=2, amount=300)
        assert buy_in_b.buy_in.id is not None
        await confirm_buy_in(uow, buy_in_id=buy_in_b.buy_in.id, admin_telegram_id=3)
        await close_room(uow, room_id=room_b.id, admin_telegram_id=3)
        # no cash-out recorded for room_b

        stats = await get_player_statistics(stats_query, telegram_id=2)

        assert stats.games_played == 2
        assert stats.total_spent == 800
        assert stats.total_buy_in_count == 2
        assert stats.total_cashed_out == 800
        assert stats.net_result == 300

    async def test_pending_and_rejected_buy_ins_are_excluded_from_spend(self) -> None:
        uow = FakeUnitOfWork()
        stats_query = FakePlayerStatisticsQuery(uow.db)
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await request_buy_in(uow, room_id=room.id, player_telegram_id=2, amount=500)

        stats = await get_player_statistics(stats_query, telegram_id=2)

        assert stats.total_spent == 0
        assert stats.total_buy_in_count == 0
