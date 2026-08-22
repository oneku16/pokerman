from datetime import UTC, datetime

import pytest

from pokerman.domain.entities import RoomPlayer
from pokerman.domain.errors import CashOutAlreadyRecordedError

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CASHED_OUT = datetime(2026, 1, 1, hour=23, tzinfo=UTC)


class TestRoomPlayerJoin:
    def test_join_creates_unpersisted_membership(self) -> None:
        member = RoomPlayer.join(room_id=7, user_telegram_id=42, now=NOW)

        assert member.id is None
        assert member.room_id == 7
        assert member.user_telegram_id == 42
        assert member.joined_at == NOW
        assert member.final_chip_count is None
        assert member.cashed_out_at is None


class TestRoomPlayerRecordCashOut:
    def test_records_chip_count_and_timestamp(self) -> None:
        member = RoomPlayer.join(room_id=7, user_telegram_id=42, now=NOW)

        member.record_cash_out(1200, CASHED_OUT)

        assert member.final_chip_count == 1200
        assert member.cashed_out_at == CASHED_OUT

    def test_zero_chip_count_is_valid(self) -> None:
        member = RoomPlayer.join(room_id=7, user_telegram_id=42, now=NOW)

        member.record_cash_out(0, CASHED_OUT)

        assert member.final_chip_count == 0

    def test_rejects_negative_chip_count(self) -> None:
        member = RoomPlayer.join(room_id=7, user_telegram_id=42, now=NOW)

        with pytest.raises(ValueError, match="negative"):
            member.record_cash_out(-1, CASHED_OUT)

    def test_rejects_recording_twice(self) -> None:
        member = RoomPlayer.join(room_id=7, user_telegram_id=42, now=NOW)
        member.record_cash_out(1200, CASHED_OUT)

        with pytest.raises(CashOutAlreadyRecordedError):
            member.record_cash_out(1300, CASHED_OUT)
