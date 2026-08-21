from datetime import UTC, datetime

from pokerman.domain.entities import RoomPlayer

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class TestRoomPlayerJoin:
    def test_join_creates_unpersisted_membership(self) -> None:
        member = RoomPlayer.join(room_id=7, user_telegram_id=42, now=NOW)

        assert member.id is None
        assert member.room_id == 7
        assert member.user_telegram_id == 42
        assert member.joined_at == NOW
