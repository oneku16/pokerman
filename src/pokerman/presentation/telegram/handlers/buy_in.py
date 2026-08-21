from aiogram import Bot, Router
from aiogram.types import CallbackQuery, Message

from pokerman.application.use_cases._buy_in_lookup import BuyInDecision
from pokerman.application.use_cases.confirm_buy_in import confirm_buy_in
from pokerman.application.use_cases.get_room import get_room
from pokerman.application.use_cases.reject_buy_in import reject_buy_in
from pokerman.application.use_cases.request_buy_in import request_buy_in
from pokerman.domain.errors import DomainError
from pokerman.presentation.telegram.callback_data import (
    BuyInCallback,
    ConfirmBuyInCallback,
    PaidCallback,
    RejectBuyInCallback,
)
from pokerman.presentation.telegram.deps import Deps
from pokerman.presentation.telegram.error_messages import describe_error
from pokerman.presentation.telegram.formatting import (
    format_buy_in_decision_for_player,
    format_buy_in_notification_for_admin,
    format_buy_in_prompt,
)
from pokerman.presentation.telegram.keyboards import admin_confirm_keyboard, buy_in_keyboard

router = Router(name="buy_in")


@router.callback_query(BuyInCallback.filter())
async def show_buy_in_prompt(
    callback: CallbackQuery, callback_data: BuyInCallback, deps: Deps
) -> None:
    assert isinstance(callback.message, Message)
    try:
        room = await get_room(deps.uow(), room_id=callback_data.room_id)
        room.ensure_active()
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return

    keyboard = buy_in_keyboard(callback_data.room_id)
    text = format_buy_in_prompt(room, room.default_buy_in_amount)
    if room.qr_file_id:
        await callback.message.answer_photo(room.qr_file_id, caption=text, reply_markup=keyboard)
    else:
        text += "\n\n(The admin hasn't uploaded a payment QR yet.)"
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(PaidCallback.filter())
async def handle_paid(
    callback: CallbackQuery, callback_data: PaidCallback, deps: Deps, bot: Bot
) -> None:
    assert callback.from_user is not None
    try:
        result = await request_buy_in(
            deps.uow(), room_id=callback_data.room_id, player_telegram_id=callback.from_user.id
        )
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return

    await callback.answer("Buy-in request sent. Waiting for the admin to confirm.")
    assert result.buy_in.id is not None
    await bot.send_message(
        result.room.admin_telegram_id,
        format_buy_in_notification_for_admin(
            callback.from_user.full_name, result.buy_in.amount, result.room.currency
        ),
        reply_markup=admin_confirm_keyboard(result.buy_in.id),
    )


@router.callback_query(ConfirmBuyInCallback.filter())
async def handle_confirm(
    callback: CallbackQuery, callback_data: ConfirmBuyInCallback, deps: Deps, bot: Bot
) -> None:
    assert callback.from_user is not None
    try:
        result = await confirm_buy_in(
            deps.uow(), buy_in_id=callback_data.buy_in_id, admin_telegram_id=callback.from_user.id
        )
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return
    await _finish_decision(callback, bot, result, confirmed=True)


@router.callback_query(RejectBuyInCallback.filter())
async def handle_reject(
    callback: CallbackQuery, callback_data: RejectBuyInCallback, deps: Deps, bot: Bot
) -> None:
    assert callback.from_user is not None
    try:
        result = await reject_buy_in(
            deps.uow(), buy_in_id=callback_data.buy_in_id, admin_telegram_id=callback.from_user.id
        )
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return
    await _finish_decision(callback, bot, result, confirmed=False)


async def _finish_decision(
    callback: CallbackQuery, bot: Bot, result: BuyInDecision, *, confirmed: bool
) -> None:
    outcome = "Confirmed" if confirmed else "Rejected"
    if isinstance(callback.message, Message) and callback.message.text:
        await callback.message.edit_text(f"{callback.message.text}\n\n{outcome} ✓")
    await callback.answer(outcome)
    await bot.send_message(
        result.player_telegram_id,
        format_buy_in_decision_for_player(
            room_name=result.room.name,
            amount=result.buy_in.amount,
            currency=result.room.currency,
            confirmed=confirmed,
        ),
    )
