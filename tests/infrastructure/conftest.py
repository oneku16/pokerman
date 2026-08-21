from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from pokerman.infrastructure.config import Settings
from pokerman.infrastructure.db.session import create_engine, create_session_factory


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    settings = Settings()
    eng = create_engine(settings.database_url)
    yield eng
    await eng.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)


@pytest_asyncio.fixture(autouse=True)
async def _clean_database(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE buy_ins, room_players, poker_rooms, users "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest_asyncio.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as s:
        yield s
