from pokerman.application.use_cases.get_user import get_user
from pokerman.application.use_cases.register_user import register_user
from tests.application.fakes import FakeUnitOfWork


class TestGetUser:
    async def test_returns_none_for_unregistered_user(self) -> None:
        uow = FakeUnitOfWork()

        user = await get_user(uow, telegram_id=1)

        assert user is None

    async def test_returns_registered_user(self) -> None:
        uow = FakeUnitOfWork()
        await register_user(uow, telegram_id=1, username="azamat", display_name="Azamat")

        user = await get_user(uow, telegram_id=1)

        assert user is not None
        assert user.display_name == "Azamat"
