from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message


async def safe_edit_text(
    message: Message, text: str, *, reply_markup: InlineKeyboardMarkup | None = None
) -> None:
    """Edit a message, silently ignoring Telegram's "message is not modified" error.

    That error fires whenever the new text and keyboard are byte-identical to what's
    already on screen (e.g. a player taps a button twice, or re-opens a dashboard that
    hasn't changed since they last looked) — harmless, so it's swallowed rather than
    crashing the update.
    """
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as error:
        if "message is not modified" not in error.message:
            raise
