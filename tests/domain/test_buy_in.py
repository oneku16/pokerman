from datetime import UTC, datetime

import pytest

from pokerman.domain.entities import BuyIn
from pokerman.domain.enums import BuyInStatus
from pokerman.domain.errors import InvalidBuyInAmountError, InvalidBuyInStateError

REQUESTED = datetime(2026, 1, 1, tzinfo=UTC)
DECIDED = datetime(2026, 1, 1, hour=1, tzinfo=UTC)
DEFAULT_AMOUNT = 500


def make_buy_in(**overrides: object) -> BuyIn:
    defaults: dict[str, object] = {
        "room_player_id": 1,
        "amount": DEFAULT_AMOUNT,
        "is_first_buy_in": True,
        "default_amount": DEFAULT_AMOUNT,
        "now": REQUESTED,
    }
    defaults.update(overrides)
    return BuyIn.request(**defaults)  # type: ignore[arg-type]


class TestBuyInRequest:
    def test_first_buy_in_matching_default_starts_pending(self) -> None:
        buy_in = make_buy_in(is_first_buy_in=True, amount=DEFAULT_AMOUNT)

        assert buy_in.id is None
        assert buy_in.amount == DEFAULT_AMOUNT
        assert buy_in.status == BuyInStatus.PENDING
        assert buy_in.requested_at == REQUESTED
        assert buy_in.decided_at is None
        assert buy_in.decided_by_telegram_id is None

    @pytest.mark.parametrize("amount", [DEFAULT_AMOUNT - 1, DEFAULT_AMOUNT + 1, 0])
    def test_first_buy_in_rejects_amount_other_than_default(self, amount: int) -> None:
        with pytest.raises(InvalidBuyInAmountError) as exc_info:
            make_buy_in(is_first_buy_in=True, amount=amount)

        assert exc_info.value.is_first_buy_in is True
        assert exc_info.value.default_amount == DEFAULT_AMOUNT
        assert exc_info.value.amount == amount

    def test_subsequent_buy_in_greater_than_default_is_allowed(self) -> None:
        buy_in = make_buy_in(is_first_buy_in=False, amount=DEFAULT_AMOUNT + 100)

        assert buy_in.amount == DEFAULT_AMOUNT + 100

    def test_subsequent_buy_in_equal_to_default_is_rejected(self) -> None:
        with pytest.raises(InvalidBuyInAmountError) as exc_info:
            make_buy_in(is_first_buy_in=False, amount=DEFAULT_AMOUNT)

        assert exc_info.value.is_first_buy_in is False

    def test_subsequent_buy_in_less_than_default_is_rejected(self) -> None:
        with pytest.raises(InvalidBuyInAmountError):
            make_buy_in(is_first_buy_in=False, amount=DEFAULT_AMOUNT - 100)

    def test_direct_construction_rejects_non_positive_amount(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            BuyIn(
                id=None,
                room_player_id=1,
                amount=0,
                status=BuyInStatus.PENDING,
                requested_at=REQUESTED,
            )


class TestBuyInConfirm:
    def test_confirm_transitions_from_pending(self) -> None:
        buy_in = make_buy_in()

        buy_in.confirm(decided_by_telegram_id=99, now=DECIDED)

        assert buy_in.status == BuyInStatus.CONFIRMED
        assert buy_in.decided_at == DECIDED
        assert buy_in.decided_by_telegram_id == 99

    def test_confirm_twice_fails(self) -> None:
        buy_in = make_buy_in()
        buy_in.confirm(decided_by_telegram_id=99, now=DECIDED)

        with pytest.raises(InvalidBuyInStateError):
            buy_in.confirm(decided_by_telegram_id=99, now=DECIDED)

    def test_confirm_after_reject_fails(self) -> None:
        buy_in = make_buy_in()
        buy_in.reject(decided_by_telegram_id=99, now=DECIDED)

        with pytest.raises(InvalidBuyInStateError):
            buy_in.confirm(decided_by_telegram_id=99, now=DECIDED)


class TestBuyInReject:
    def test_reject_transitions_from_pending(self) -> None:
        buy_in = make_buy_in()

        buy_in.reject(decided_by_telegram_id=99, now=DECIDED)

        assert buy_in.status == BuyInStatus.REJECTED
        assert buy_in.decided_at == DECIDED
        assert buy_in.decided_by_telegram_id == 99

    def test_reject_twice_fails(self) -> None:
        buy_in = make_buy_in()
        buy_in.reject(decided_by_telegram_id=99, now=DECIDED)

        with pytest.raises(InvalidBuyInStateError):
            buy_in.reject(decided_by_telegram_id=99, now=DECIDED)

    def test_reject_after_confirm_fails(self) -> None:
        buy_in = make_buy_in()
        buy_in.confirm(decided_by_telegram_id=99, now=DECIDED)

        with pytest.raises(InvalidBuyInStateError):
            buy_in.reject(decided_by_telegram_id=99, now=DECIDED)
