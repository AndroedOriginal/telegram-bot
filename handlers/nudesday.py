from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import ContextTypes

from handlers.events import scheduler
from handlers.fuck_storage import set_fuck_enabled
from handlers.nudesday_storage import (
    is_nudesday_enabled,
    set_nudesday_enabled,
    get_all_nudesday_chats,
)
from utils.permissions import require_admin


_bot = None


def _job_id(chat_id):
    return f"nudesday_{chat_id}"


async def _start_nudesday(chat_id):
    # Команда "fuck" становится доступна всем ровно на сутки — до
    # начала пятницы, дальше is_fuck_enabled сама всё выключит.
    until = datetime.now(timezone.utc) + timedelta(hours=24)
    set_fuck_enabled(chat_id, until)

    try:
        await _bot.send_message(
            chat_id=chat_id,
            text="Объявляется нюдсочетверг."
        )
    except Exception as e:
        print(f"NUDESDAY ERROR: {chat_id} | {repr(e)}")
        return

    print(
        f"NUDESDAY: запущен в чате {chat_id}, "
        "команда fuck включена на сутки"
    )


def _add_job(chat_id):
    # Используем общий планировщик из handlers.events (та же таймзона,
    # Europe/Moscow), чтобы не поднимать второй AsyncIOScheduler.
    scheduler.add_job(
        _start_nudesday,
        "cron",
        day_of_week="thu",
        hour=0,
        minute=0,
        args=[chat_id],
        id=_job_id(chat_id),
        replace_existing=True
    )


def _remove_job(chat_id):
    try:
        scheduler.remove_job(_job_id(chat_id))
    except Exception:
        pass


def init_nudesday(bot):
    global _bot
    _bot = bot

    for chat_id in get_all_nudesday_chats():
        _add_job(chat_id)


async def nudesday_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.effective_message
    chat = update.effective_chat

    if not await require_admin(update, context):
        return

    args = context.args

    try:
        await message.delete()
    except Exception:
        pass

    if not args or args[0].lower() not in ("on", "off"):
        await chat.send_message(
            "Используй: /nudesday on либо /nudesday off"
        )
        return

    if args[0].lower() == "off":
        set_nudesday_enabled(chat.id, False)
        _remove_job(chat.id)

        await chat.send_message(
            "Нюдсочетверг выключен для этого чата."
        )
        return

    set_nudesday_enabled(chat.id, True)
    _add_job(chat.id)

    await chat.send_message(
        "Нюдсочетверг включён — каждый четверг в 00:00 по Москве в чате "
        "объявляется нюдсочетверг, и на сутки команда «fuck» становится "
        "доступна всем участникам."
    )
