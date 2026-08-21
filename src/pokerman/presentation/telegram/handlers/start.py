from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart, StateFilter
from aiogram.types import Message

from pokerman.application.use_cases.join_room import join_room_by_code, join_room_by_deep_link
from pokerman.application.use_cases.list_rooms_for_user import list_rooms_for_user
from pokerman.domain.errors import DomainError
from pokerman.presentation.telegram.deps import Deps
from pokerman.presentation.telegram.error_messages import describe_error
from pokerman.presentation.telegram.keyboards import main_menu_keyboard, room_dashboard_keyboard

router = Router(name="start")

WELCOME_TEXT = (
    "Welcome to Pokerman — a room manager and buy-in ledger for private poker games.\n\n"
    "Create a room, or join one with its 4-digit code."
)


@router.message(CommandStart(deep_link=True))
async def start_with_deep_link(message: Message, command: CommandObject, deps: Deps) -> None:
    assert message.from_user is not None
    token = command.args
    if not token:
        await message.answer(WELCOME_TEXT)
        return
    try:
        room = await join_room_by_deep_link(
            deps.uow(),
            token=token,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            display_name=message.from_user.full_name,
        )
    except DomainError as error:
        await message.answer(describe_error(error))
        return
    await message.answer(
        f"Joined {room.name}.",
        reply_markup=room_dashboard_keyboard(room, is_admin=False),
    )


@router.message(CommandStart())
async def start_plain(message: Message, deps: Deps) -> None:
    assert message.from_user is not None
    rooms = await list_rooms_for_user(deps.uow(), telegram_id=message.from_user.id)
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard(rooms))


@router.message(StateFilter(None), F.text.regexp(r"^\d{4}$"))
async def join_by_typed_code(message: Message, deps: Deps) -> None:
    assert message.from_user is not None
    assert message.text is not None
    try:
        room = await join_room_by_code(
            deps.uow(),
            code=message.text,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            display_name=message.from_user.full_name,
        )
    except DomainError as error:
        await message.answer(describe_error(error))
        return
    await message.answer(
        f"Joined {room.name}.",
        reply_markup=room_dashboard_keyboard(room, is_admin=False),
    )
