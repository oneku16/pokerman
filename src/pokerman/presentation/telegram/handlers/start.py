from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from pokerman.application.use_cases.get_user import get_user
from pokerman.application.use_cases.join_room import join_room_by_code, join_room_by_deep_link
from pokerman.application.use_cases.register_user import register_user
from pokerman.domain.entities import PokerRoom
from pokerman.domain.errors import DomainError
from pokerman.presentation.telegram.deps import Deps
from pokerman.presentation.telegram.error_messages import describe_error
from pokerman.presentation.telegram.formatting import format_help_text
from pokerman.presentation.telegram.keyboards import main_menu_keyboard, room_dashboard_keyboard
from pokerman.presentation.telegram.states import CreateRoomStates, RegistrationStates

router = Router(name="start")

WELCOME_TEXT = (
    "Welcome to Pokerman — a room manager and buy-in ledger for private poker games.\n\n"
    "Create a room, or join one with its 4-digit code.\n\n"
    "New here? Send /help for a quick tour."
)

GREETING_FOR_NEW_USER = (
    "👋 Welcome to Pokerman!\n\n"
    "I keep the books for private poker games — who bought in, for how much, and how "
    "everyone finished. I never hold or move money; you pay your host directly and I "
    "just record it.\n\n"
    "Send /help any time for the full rundown."
)

_MAX_NAME_LENGTH = 64


async def ensure_registered_or_ask(
    message: Message,
    *,
    telegram_id: int,
    deps: Deps,
    state: FSMContext,
    pending_type: str,
    pending_value: str | None = None,
) -> bool:
    user = await get_user(deps.uow(), telegram_id=telegram_id)
    if user is not None:
        return True
    await state.update_data(pending_type=pending_type, pending_value=pending_value)
    await state.set_state(RegistrationStates.waiting_for_display_name)
    await message.answer(
        "Before we start — what's your name? This is how other players will see you."
    )
    return False


@router.message(RegistrationStates.waiting_for_display_name)
async def receive_display_name(message: Message, state: FSMContext, deps: Deps) -> None:
    assert message.from_user is not None
    name = (message.text or "").strip()
    if not name:
        await message.answer("Please send your name as text.")
        return
    if len(name) > _MAX_NAME_LENGTH:
        await message.answer(
            f"That's a bit long — please send a shorter name (up to {_MAX_NAME_LENGTH} characters)."
        )
        return

    await register_user(
        deps.uow(),
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        display_name=name,
    )

    data = await state.get_data()
    pending_type = data.get("pending_type")
    pending_value = data.get("pending_value")
    await state.clear()

    if pending_type == "join_deep_link":
        assert pending_value is not None
        await _complete_deep_link_join(
            message,
            deps,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            display_name=name,
            token=pending_value,
        )
    elif pending_type == "join_code":
        assert pending_value is not None
        await _complete_code_join(
            message,
            deps,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            display_name=name,
            code=pending_value,
        )
    elif pending_type == "create_room":
        await state.set_state(CreateRoomStates.waiting_for_name)
        await message.answer("What should the room be called?")
    else:
        await message.answer(GREETING_FOR_NEW_USER)
        await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())


@router.message(CommandStart(deep_link=True))
async def start_with_deep_link(
    message: Message, command: CommandObject, deps: Deps, state: FSMContext
) -> None:
    assert message.from_user is not None
    token = command.args
    if not token:
        await message.answer(WELCOME_TEXT)
        return
    registered = await ensure_registered_or_ask(
        message,
        telegram_id=message.from_user.id,
        deps=deps,
        state=state,
        pending_type="join_deep_link",
        pending_value=token,
    )
    if not registered:
        return
    await _complete_deep_link_join(
        message,
        deps,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        display_name=message.from_user.full_name,
        token=token,
    )


async def _complete_deep_link_join(
    message: Message,
    deps: Deps,
    *,
    telegram_id: int,
    username: str | None,
    display_name: str,
    token: str,
) -> None:
    try:
        room = await join_room_by_deep_link(
            deps.uow(),
            token=token,
            telegram_id=telegram_id,
            username=username,
            display_name=display_name,
        )
    except DomainError as error:
        await message.answer(describe_error(error))
        return
    await message.answer(
        f"Joined {room.name}.",
        reply_markup=room_dashboard_keyboard(room, is_admin=False),
    )


@router.message(CommandStart())
async def start_plain(message: Message, deps: Deps, state: FSMContext) -> None:
    assert message.from_user is not None
    registered = await ensure_registered_or_ask(
        message,
        telegram_id=message.from_user.id,
        deps=deps,
        state=state,
        pending_type="menu",
    )
    if not registered:
        return
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(format_help_text())


@router.message(StateFilter(None), F.text.regexp(r"^\d{4}$"))
async def join_by_typed_code(message: Message, deps: Deps, state: FSMContext) -> None:
    assert message.from_user is not None
    assert message.text is not None
    registered = await ensure_registered_or_ask(
        message,
        telegram_id=message.from_user.id,
        deps=deps,
        state=state,
        pending_type="join_code",
        pending_value=message.text,
    )
    if not registered:
        return
    await _complete_code_join(
        message,
        deps,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        display_name=message.from_user.full_name,
        code=message.text,
    )


async def _complete_code_join(
    message: Message,
    deps: Deps,
    *,
    telegram_id: int,
    username: str | None,
    display_name: str,
    code: str,
) -> PokerRoom | None:
    try:
        room = await join_room_by_code(
            deps.uow(),
            code=code,
            telegram_id=telegram_id,
            username=username,
            display_name=display_name,
        )
    except DomainError as error:
        await message.answer(describe_error(error))
        return None
    await message.answer(
        f"Joined {room.name}.",
        reply_markup=room_dashboard_keyboard(room, is_admin=False),
    )
    return room
