from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pokerman.presentation.telegram.deps import Deps
from pokerman.presentation.telegram.handlers import buy_in, dashboard, room_admin, start


def build_bot(token: str) -> Bot:
    return Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def build_dispatcher(
    *, session_factory: async_sessionmaker[AsyncSession], bot_username: str, default_currency: str
) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(room_admin.router)
    dispatcher.include_router(buy_in.router)
    dispatcher.include_router(dashboard.router)
    dispatcher.include_router(start.router)
    dispatcher["deps"] = Deps(
        session_factory=session_factory,
        bot_username=bot_username,
        default_currency=default_currency,
    )
    return dispatcher
