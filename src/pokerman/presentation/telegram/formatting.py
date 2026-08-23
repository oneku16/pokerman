import html

from pokerman.application.read_models import PlayerStatistics
from pokerman.application.use_cases.get_player_history import PlayerHistory
from pokerman.application.use_cases.get_room_dashboard import RoomDashboard
from pokerman.domain.entities import PokerRoom, User
from pokerman.domain.enums import RoomStatus


def esc(text: str) -> str:
    return html.escape(text)


def deep_link(bot_username: str, room: PokerRoom) -> str:
    return f"https://t.me/{bot_username}?start={room.deep_link_token}"


def format_room_created(room: PokerRoom, bot_username: str) -> str:
    return (
        f"<b>{esc(room.name)}</b> is open.\n\n"
        f"Room code: <code>{room.code}</code>\n"
        f"Deep link: {deep_link(bot_username, room)}\n"
        f"Default buy-in: {room.default_buy_in_amount} {esc(room.currency)}\n\n"
        "Share the code or the link with your players. Upload a payment QR from "
        "the room menu so players can pay you."
    )


def format_dashboard(dashboard: RoomDashboard) -> str:
    room = dashboard.room
    title = "Final ledger" if room.status == RoomStatus.CLOSED else "Dashboard"
    rows = sorted(dashboard.players, key=lambda r: r.confirmed_total, reverse=True)

    lines = [f"{room.name} — {title}", ""]
    if rows:
        name_width = max(8, max(len(r.display_name) for r in rows))
        lines.append(f"{'Player'.ljust(name_width)}  {'Total'.rjust(10)}  Buy-ins")
        for row in rows:
            total = f"{row.confirmed_total} {room.currency}"
            lines.append(
                f"{row.display_name.ljust(name_width)}  {total.rjust(10)}  {row.confirmed_count}"
            )
    else:
        lines.append("No players yet.")
    lines.append("")
    lines.append(f"Total: {dashboard.total_confirmed} {room.currency}")

    return f"<pre>{esc("\n".join(lines))}</pre>"


def format_player_history(history: PlayerHistory, display_name: str) -> str:
    room = history.room
    lines = [display_name, f"Total confirmed: {history.confirmed_total} {room.currency}", ""]
    if not history.buy_ins:
        lines.append("No buy-ins yet.")
    else:
        ordered = sorted(history.buy_ins, key=lambda b: b.requested_at)
        for index, buy_in in enumerate(ordered, start=1):
            lines.append(f"#{index} +{buy_in.amount} {room.currency} — {buy_in.status.value}")

    return f"<pre>{esc("\n".join(lines))}</pre>"


def format_buy_in_prompt(room: PokerRoom, amount: int) -> str:
    return (
        f"Buy-in for <b>{esc(room.name)}</b>: {amount} {esc(room.currency)}.\n\n"
        'Scan the QR above, transfer the money, then press "I Paid".'
    )


def format_buy_in_notification_for_admin(display_name: str, amount: int, currency: str) -> str:
    return f"<b>{esc(display_name)}</b> requested a buy-in\n{amount} {esc(currency)}"


def format_buy_in_decision_for_player(
    *, room_name: str, amount: int, currency: str, confirmed: bool
) -> str:
    outcome = "confirmed" if confirmed else "rejected"
    return f"Your buy-in of {amount} {esc(currency)} in {esc(room_name)} was {outcome}."


def format_cash_out_prompt(room: PokerRoom) -> str:
    return (
        f"<b>{esc(room.name)}</b> has closed.\n\n"
        "Tap below and tell us how many chips you finished with, so we can work out "
        "your result."
    )


def format_cash_out_confirmation(*, chip_count: int, total_spent: int, currency: str) -> str:
    net = chip_count - total_spent
    sign = "+" if net >= 0 else ""
    return (
        f"You entered {chip_count} {esc(currency)}.\n"
        f"Total buy-in: {total_spent} {esc(currency)}.\n"
        f"Net result: {sign}{net} {esc(currency)}.\n\n"
        "Confirm this is correct, or re-enter."
    )


def format_cash_out_recorded(net_result: int, currency: str) -> str:
    sign = "+" if net_result >= 0 else ""
    return f"Recorded. Your net result: {sign}{net_result} {esc(currency)}."


def format_help_text() -> str:
    return (
        "<b>Pokerman — how it works</b>\n\n"
        "Pokerman keeps the books for a private poker game. It never holds, moves, or "
        "processes money — you pay the room's host directly, and the bot just records "
        "who bought in for how much.\n\n"
        "<b>Playing</b>\n"
        "• Join a room with its 4-digit code or an invite link.\n"
        "• Tap <b>Buy In</b>, pick an amount, and you'll see the host's payment QR.\n"
        "• Transfer the money, then tap <b>I Paid</b>.\n"
        "• The host confirms it, and only then does it count toward the totals.\n\n"
        "<b>Hosting</b>\n"
        "• Create a room and share the code or link.\n"
        "• Upload a payment QR so players know where to send money.\n"
        "• Confirm or reject each buy-in request as it comes in.\n"
        "• Close the room when the game ends — everyone is asked for their final "
        "chip count, and the bot works out each player's result.\n\n"
        "<b>Commands</b>\n"
        "/start — main menu\n"
        "/dashboard — current room standings\n"
        "/statistics — your lifetime totals\n"
        "/settings — your name, saved QR, and spending limit\n"
        "/help — this message"
    )


def format_settings(user: User, currency: str) -> str:
    if user.spending_limit is None:
        limit_line = "Spending limit: none"
    else:
        limit_line = f"Spending limit: {user.spending_limit} {currency} per room"
    qr_line = "Saved QR: yes" if user.default_qr_file_id else "Saved QR: none"

    return (
        "<b>Settings</b>\n\n"
        f"Name: {esc(user.display_name)}\n"
        f"{qr_line}\n"
        f"{limit_line}\n\n"
        "<i>A spending limit caps how much you can buy in for within a single room. "
        "Once set, it can only be changed once every 7 days.</i>"
    )


def format_statistics(stats: PlayerStatistics, currency: str) -> str:
    sign = "+" if stats.net_result >= 0 else ""
    lines = [
        f"{stats.display_name} — Statistics",
        "",
        f"Games played: {stats.games_played}",
        f"Buy-ins: {stats.total_buy_in_count} ({stats.total_spent} {currency})",
        f"Cashed out: {stats.total_cashed_out} {currency}",
        f"Net result: {sign}{stats.net_result} {currency}",
    ]
    return f"<pre>{esc("\n".join(lines))}</pre>"
