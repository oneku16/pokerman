import hmac
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiogram.types import BotCommand, Update
from fastapi import FastAPI, Header, HTTPException, Request

from pokerman.infrastructure.config import Settings
from pokerman.infrastructure.db.session import create_engine, create_session_factory
from pokerman.presentation.telegram.bot import build_bot, build_dispatcher

logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/telegram/webhook"


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
        app.state.bot = bot
        app.state.dispatcher = dispatcher

        await bot.set_webhook(
            url=f"{settings.public_base_url}{WEBHOOK_PATH}",
            secret_token=settings.telegram_webhook_secret,
        )
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Main menu"),
                BotCommand(command="dashboard", description="Your current or last game"),
                BotCommand(command="history", description="Pick from your last 10 rooms"),
                BotCommand(command="statistics", description="Your lifetime totals"),
                BotCommand(command="settings", description="Name, saved QR, spending limit"),
                BotCommand(command="help", description="How Pokerman works"),
            ]
        )
        try:
            yield
        finally:
            await bot.session.close()
            await engine.dispose()

    app = FastAPI(title="Pokerman", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(WEBHOOK_PATH)
    async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: str | None = Header(default=None),
    ) -> dict[str, str]:
        if not hmac.compare_digest(
            x_telegram_bot_api_secret_token or "", settings.telegram_webhook_secret
        ):
            raise HTTPException(status_code=401, detail="invalid secret token")

        bot = request.app.state.bot
        dispatcher = request.app.state.dispatcher
        update = Update.model_validate(await request.json(), context={"bot": bot})
        try:
            await dispatcher.feed_update(bot, update)
        except Exception:
            # A single handler bug must not surface as a 500 — Telegram would just
            # keep retrying the same update. Log it and acknowledge the delivery.
            logger.exception("Unhandled error while processing update %s", update.update_id)
        return {"status": "ok"}

    return app
