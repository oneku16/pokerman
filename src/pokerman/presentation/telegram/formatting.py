import html

from pokerman.application.use_cases.get_player_history import PlayerHistory
from pokerman.application.use_cases.get_room_dashboard import RoomDashboard
from pokerman.domain.entities import PokerRoom
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
    rows = sorted(dashboard.players, key=lambda r: r.display_name.lower())

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
