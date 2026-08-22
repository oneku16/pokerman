from pokerman.application.use_cases.register_user import register_user
from tests.application.fakes import FakeUnitOfWork


class TestRegisterUser:
    async def test_registers_a_new_user(self) -> None:
        uow = FakeUnitOfWork()

        user = await register_user(uow, telegram_id=1, username="azamat", display_name="Azamat")

        assert user.telegram_id == 1
        assert user.display_name == "Azamat"
        assert user.username == "azamat"
        assert uow.committed is True

    async def test_does_not_overwrite_display_name_on_repeat_registration(self) -> None:
        uow = FakeUnitOfWork()
        await register_user(uow, telegram_id=1, username="old", display_name="Chosen Name")

        user = await register_user(
            uow, telegram_id=1, username="new", display_name="Different Name"
        )

        assert user.display_name == "Chosen Name"
        assert user.username == "new"
