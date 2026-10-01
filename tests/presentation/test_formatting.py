from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from pokerman.domain.entities import PokerRoom
from pokerman.domain.value_objects import RoomCode
from pokerman.presentation.telegram.formatting import format_planned_end

BISHKEK = ZoneInfo("Asia/Bishkek")
CREATED = datetime(2026, 1, 1, 14, 0, tzinfo=UTC)  # 20:00 in Bishkek (UTC+6)


def _room(planned_duration_hours: int | None) -> PokerRoom:
    return PokerRoom.open(
        name="Poker Night",
        code=RoomCode("4821"),
        deep_link_token="tok",
        default_buy_in_amount=500,
        currency="KGS",
        admin_telegram_id=1,
        now=CREATED,
        planned_duration_hours=planned_duration_hours,
    )


class TestFormatPlannedEnd:
    def test_none_without_a_planned_duration(self) -> None:
        assert format_planned_end(_room(None), BISHKEK, now=CREATED) is None

    def test_shows_local_leave_time_and_time_left(self) -> None:
        text = format_planned_end(_room(4), BISHKEK, now=CREATED + timedelta(minutes=75))

        assert text == "Leave time: 00:00 (4h session), 2h 45m left"

    def test_under_an_hour_left_shows_minutes_only(self) -> None:
        text = format_planned_end(_room(3), BISHKEK, now=CREATED + timedelta(minutes=170))

        assert text == "Leave time: 23:00 (3h session), 10m left"

    def test_flags_when_time_is_up(self) -> None:
        text = format_planned_end(_room(3), BISHKEK, now=CREATED + timedelta(hours=4))

        assert text == "Leave time: 23:00 (3h session), time's up"

    def test_closed_room_shows_only_the_leave_time(self) -> None:
        room = _room(3)
        room.close(CREATED + timedelta(hours=1))

        assert format_planned_end(room, BISHKEK) == "Leave time: 23:00 (3h session)"
