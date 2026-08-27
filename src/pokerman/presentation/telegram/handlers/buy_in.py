from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from pokerman.application.use_cases._buy_in_lookup import BuyInDecision
from pokerman.application.use_cases.confirm_buy_in import confirm_buy_in
from pokerman.application.use_cases.get_room import get_room
from pokerman.application.use_cases.reject_buy_in import reject_buy_in
from pokerman.application.use_cases.request_buy_in import request_buy_in
from pokerman.domain.entities import PokerRoom
from pokerman.domain.errors import DomainError
from pokerman.presentation.telegram.callback_data import (
    BuyInAmountCallback,
    BuyInCallback,
    BuyInOtherCallback,
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
from pokerman.presentation.telegram.keyboards import (
    admin_confirm_keyboard,
    buy_in_amount_keyboard,
    buy_in_keyboard,
)
from pokerman.presentation.telegram.messaging import safe_edit_text
from pokerman.presentation.telegram.parsing import parse_positive_amount
from pokerman.presentation.telegram.states import BuyInStates

router = Router(name="buy_in")


@router.callback_query(BuyInCallback.filter())
async def show_amount_picker(
    callback: CallbackQuery, callback_data: BuyInCallback, deps: Deps
) -> None:
    assert isinstance(callback.message, Message)
    try:
        room = await get_room(deps.uow(), room_id=callback_data.room_id)
        room.ensure_active()
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return

    await callback.message.answer(
        "How much are you buying in for?",
        reply_markup=buy_in_amount_keyboard(callback_data.room_id),
    )
    await callback.answer()


@router.callback_query(BuyInAmountCallback.filter())
async def handle_preset_amount(
    callback: CallbackQuery, callback_data: BuyInAmountCallback, deps: Deps
) -> None:
    assert isinstance(callback.message, Message)
    try:
        room = await get_room(deps.uow(), room_id=callback_data.room_id)
        room.ensure_active()
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return

    await _show_payment_step(callback.message, room, callback_data.amount)
    await callback.answer()


@router.callback_query(BuyInOtherCallback.filter())
async def start_custom_amount(
    callback: CallbackQuery, callback_data: BuyInOtherCallback, state: FSMContext
) -> None:
    assert isinstance(callback.message, Message)
    await state.update_data(room_id=callback_data.room_id)
    await state.set_state(BuyInStates.waiting_for_custom_amount)
    await callback.message.answer("Enter your buy-in amount.")
    await callback.answer()


@router.message(BuyInStates.waiting_for_custom_amount)
async def receive_custom_amount(message: Message, state: FSMContext, deps: Deps) -> None:
    amount = parse_positive_amount(message.text or "")
    if amount is None:
        await message.answer("Please send a positive whole number, e.g. 500.")
        return

    data = await state.get_data()
    await state.clear()
    try:
        room = await get_room(deps.uow(), room_id=data["room_id"])
        room.ensure_active()
    except DomainError as error:
        await message.answer(describe_error(error))
        return

    await _show_payment_step(message, room, amount)


async def _show_payment_step(message: Message, room: PokerRoom, amount: int) -> None:
    assert room.id is not None
    keyboard = buy_in_keyboard(room.id, amount)
    text = format_buy_in_prompt(room, amount)
    if room.qr_file_id:
        await message.answer_photo(room.qr_file_id, caption=text, reply_markup=keyboard)
    else:
        text += "\n\n(The admin hasn't uploaded a payment QR yet.)"
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(PaidCallback.filter())
async def handle_paid(
    callback: CallbackQuery, callback_data: PaidCallback, deps: Deps, bot: Bot
) -> None:
    assert callback.from_user is not None
    try:
        result = await request_buy_in(
            deps.uow(),
            room_id=callback_data.room_id,
            player_telegram_id=callback.from_user.id,
            amount=callback_data.amount,
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
        await safe_edit_text(callback.message, f"{callback.message.text}\n\n{outcome} ✓")
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
