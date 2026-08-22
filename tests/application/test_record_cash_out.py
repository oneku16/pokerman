import pytest

from pokerman.application.use_cases.close_room import close_room
from pokerman.application.use_cases.record_cash_out import record_cash_out
from pokerman.domain.errors import (
    CashOutAlreadyRecordedError,
    NotRoomMemberError,
    RoomNotClosedError,
    RoomNotFoundError,
)
from tests.application.fakes import FakeUnitOfWork
from tests.application.helpers import add_player, make_room


class TestRecordCashOut:
    async def test_records_cash_out_for_closed_room(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await close_room(uow, room_id=room.id, admin_telegram_id=1)

        member = await record_cash_out(
            uow, room_id=room.id, player_telegram_id=2, chip_count=1200
        )

        assert member.final_chip_count == 1200
        assert member.cashed_out_at is not None
        assert uow.committed is True

    async def test_zero_chip_count_is_recorded(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await close_room(uow, room_id=room.id, admin_telegram_id=1)

        member = await record_cash_out(uow, room_id=room.id, player_telegram_id=2, chip_count=0)

        assert member.final_chip_count == 0

    async def test_rejects_recording_before_room_is_closed(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")

        with pytest.raises(RoomNotClosedError):
            await record_cash_out(uow, room_id=room.id, player_telegram_id=2, chip_count=1200)

    async def test_unknown_room_raises_not_found(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(RoomNotFoundError):
            await record_cash_out(uow, room_id=404, player_telegram_id=1, chip_count=1200)

    async def test_non_member_cannot_record_cash_out(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await close_room(uow, room_id=room.id, admin_telegram_id=1)

        with pytest.raises(NotRoomMemberError):
            await record_cash_out(uow, room_id=room.id, player_telegram_id=99, chip_count=1200)

    async def test_rejects_recording_twice(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await close_room(uow, room_id=room.id, admin_telegram_id=1)
        await record_cash_out(uow, room_id=room.id, player_telegram_id=2, chip_count=1200)

        with pytest.raises(CashOutAlreadyRecordedError):
            await record_cash_out(uow, room_id=room.id, player_telegram_id=2, chip_count=1300)
