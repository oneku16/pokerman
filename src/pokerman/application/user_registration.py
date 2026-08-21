from datetime import UTC, datetime

from pokerman.application.ports import UserRepository
from pokerman.domain.entities import User


async def upsert_user(
    users: UserRepository, *, telegram_id: int, username: str | None, display_name: str
) -> User:
    user = await users.get_by_telegram_id(telegram_id)
    if user is None:
        return await users.add(
            User.register(
                telegram_id=telegram_id,
                username=username,
                display_name=display_name,
                now=datetime.now(UTC),
            )
        )
    user.refresh_profile(username=username, display_name=display_name)
    await users.save(user)
    return user
