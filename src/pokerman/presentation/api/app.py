import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from pokerman.infrastructure.config import Settings
from pokerman.infrastructure.db.session import create_engine, create_session_factory
from pokerman.presentation.telegram.bot import build_bot, build_dispatcher


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings.database_url)
        session_factory = create_session_factory(engine)
        bot = build_bot(settings.telegram_bot_token)
        dispatcher = build_dispatcher(
            session_factory=session_factory,
            bot_username=settings.telegram_bot_username,
            default_currency=settings.default_currency,
        )
        polling_task = asyncio.create_task(dispatcher.start_polling(bot, handle_signals=False))
        try:
            yield
        finally:
            polling_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await polling_task
            await bot.session.close()
            await engine.dispose()

    app = FastAPI(title="Pokerman", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
