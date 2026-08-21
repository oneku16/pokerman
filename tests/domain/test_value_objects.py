import pytest

from pokerman.domain.value_objects import RoomCode


class TestRoomCode:
    def test_accepts_four_digits(self) -> None:
        assert RoomCode("4821").value == "4821"

    def test_accepts_leading_zeros(self) -> None:
        assert RoomCode("0007").value == "0007"

    @pytest.mark.parametrize(
        "value",
        ["482", "48212", "abcd", "", "48-1", " 4821"],
    )
    def test_rejects_invalid_formats(self, value: str) -> None:
        with pytest.raises(ValueError, match="4 digits"):
            RoomCode(value)

    def test_generate_produces_valid_code(self) -> None:
        code = RoomCode.generate()
        assert len(code.value) == 4
        assert code.value.isdigit()

    def test_str_returns_raw_value(self) -> None:
        assert str(RoomCode("1234")) == "1234"

    def test_equality_is_by_value(self) -> None:
        assert RoomCode("1234") == RoomCode("1234")
        assert RoomCode("1234") != RoomCode("4321")
