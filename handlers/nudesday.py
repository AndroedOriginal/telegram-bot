from telegram import Update
from telegram.ext import ContextTypes

from handlers.events import scheduler
from handlers.nudesday_storage import (
    set_nudesday,
    is_nudesday_enabled,
    get_enabled_chats
)


ANNOUNCE_TEXT = "Объявляется нюдсочетверг."

_bot = None


def _resolve_chat_id(chat_id):
    try:
        return int(chat_id)
    except (TypeError, ValueError):
        return chat_id


async def _announce_nudesday():
    for chat_id in get_enabled_chats():
        try:
            await _bot.send_message(
                chat_id=_resolve_chat_id(chat_id),
                text=ANNOUNCE_TEXT
            )

            print(f"NUDESDAY: анонс отправлен в {chat_id}")

        except Exception as e:
            print(f"NUDESDAY ERROR: {chat_id} | {repr(e)}")


def init_nudesday(bot):
    """
    Вешает еженедельную задачу на ОБЩИЙ планировщик из handlers/events.py —
    отдельный планировщик не нужен. Каждый четверг в 00:00 по Москве во
    все чаты с включённым нюдсочетвергом уходит анонс. Доступ к /fuck
    по дням недели (см. handlers/fuck.py) считается на лету и никакого
    отдельного "выключения в конце дня" не требует.
    """
    global _bot
    _bot = bot

    scheduler.add_job(
        _announce_nudesday,
        "cron",
        day_of_week="thu",
        hour=0,
        minute=0,
        id="nudesday_announce",
        replace_existing=True
    )

    print("Нюдсочетверг: еженедельная задача запланирована")


async def nudesday_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.effective_message
    chat = update.effective_chat
    actor = update.effective_user

    admins = await context.bot.get_chat_administrators(chat.id)
    owner_id = next(
        (a.user.id for a in admins if a.status == "creator"),
        None
    )

    try:
        await message.delete()
    except Exception:
        pass

    # Только владелец чата может включать/выключать нюдсочетверг —
    # так же, как и тумблер /fuck.
    if actor.id != owner_id:
        return

    args = list(context.args) if context.args else []

    if not args or args[0].lower() not in ("on", "off"):
        await chat.send_message(
            "Используй: /nudesday on либо /nudesday off"
        )
        return

    enabled = args[0].lower() == "on"
    set_nudesday(chat.id, enabled)

    if enabled:
        await chat.send_message(
            "Нюдсочетверг включён 🔞\n\n"
            "Каждый четверг в 00:00 (МСК) в чат придёт анонс, и весь "
            "этот день /fuck будет доступен всем участникам. Админы "
            "могут пользоваться /fuck в любой день, пока нюдсочетверг "
            "включён."
        )
    else:
        await chat.send_message("Нюдсочетверг выключён.")
