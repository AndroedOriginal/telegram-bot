import re
from html import escape

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from telegram import Update
from telegram.ext import ContextTypes

from handlers.events_storage import (
    get_chat_events,
    set_chat_event,
    delete_chat_event,
    get_all_events
)


TIMEZONE = pytz.timezone("Europe/Moscow")

NAME_RE = re.compile(r"^[\w-]+$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

# Этому чату события были настроены вручную через config.json ещё до
# появления системы именованных событий — при первом запуске сохраняем
# ему прежнее расписание, чтобы оно не прервалось.
LEGACY_CHAT_ID = "@old_nbrg_chat"

scheduler = AsyncIOScheduler(timezone=TIMEZONE)

_bot = None


def _job_id(chat_id, name):
    return f"event_{chat_id}_{name}"


def _resolve_chat_id(chat_id):
    # events.json хранит ключи чатов как строки (так требует JSON),
    # но send_message для числового id ждёт именно int.
    try:
        return int(chat_id)
    except (TypeError, ValueError):
        return chat_id


async def _send_event(chat_id, text):
    try:
        await _bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML"
        )

        print(f"EVENT: отправлено в {chat_id}")

    except Exception as e:
        print(f"EVENT ERROR: {chat_id} | {repr(e)}")


def _add_job(chat_id, name, time_str, text):
    hour, minute = map(int, time_str.split(":"))

    scheduler.add_job(
        _send_event,
        "cron",
        hour=hour,
        minute=minute,
        args=[_resolve_chat_id(chat_id), text],
        id=_job_id(chat_id, name),
        replace_existing=True
    )


def schedule_event(chat_id, name, time_str, text):
    name = name.lower()

    set_chat_event(chat_id, name, time_str, text)
    _add_job(chat_id, name, time_str, text)


def remove_event(chat_id, name):
    name = name.lower()

    removed = delete_chat_event(chat_id, name)

    if removed:
        try:
            scheduler.remove_job(_job_id(chat_id, name))
        except Exception:
            pass

    return removed


def init_events(bot):
    global _bot
    _bot = bot

    # Одноразовая миграция старого чата (см. LEGACY_CHAT_ID выше).
    get_chat_events(LEGACY_CHAT_ID)

    for chat_id, events in get_all_events().items():
        for name, event in events.items():
            _add_job(chat_id, name, event["time"], event["text"])

    scheduler.start()
    print("Планировщик событий запущен")


async def _check_admin(update, context):
    chat = update.effective_chat

    admins = await context.bot.get_chat_administrators(chat.id)
    admin_ids = [admin.user.id for admin in admins]

    if update.effective_user.id in admin_ids:
        return True

    try:
        await update.effective_message.delete()
    except Exception as e:
        print("EVENT: ошибка удаления сообщения", repr(e))
        pass

    return False


async def addevent_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    # update.message пустой для отредактированных сообщений — команда,
    # присланная правкой уже отправленного текста, иначе рушила хендлер.
    message = update.effective_message
    chat = update.effective_chat

    if not await _check_admin(update, context):
        return

    # re.split с maxsplit сохраняет пробелы/переносы строк/спойлеры
    # в тексте события без изменений.
    parts = re.split(r"\s+", message.text, maxsplit=3)

    if len(parts) < 4:
        await message.reply_text(
            "Используй: /addevent название время текст\n"
            "Например: /addevent movie 20:00 Сегодня смотрим фильм!"
        )
        return

    _, name, time_str, text = parts

    if not NAME_RE.match(name):
        await message.reply_text(
            "Название события может содержать только буквы, цифры, "
            "_ и -, без пробелов."
        )
        return

    if not TIME_RE.match(time_str):
        await message.reply_text(
            "Неверный формат времени. Используй формат ЧЧ:ММ, "
            "например 20:00"
        )
        return

    name = name.lower()

    if name in get_chat_events(chat.id):
        await message.reply_text(
            f"Событие «{escape(name)}» уже существует. Используй "
            "/setevent, чтобы изменить его."
        )
        return

    schedule_event(chat.id, name, time_str, text)

    try:
        await message.delete()
    except Exception:
        pass

    await chat.send_message(
        f"Добавлен ивент «{escape(name)}».\n"
        f"Час: «{time_str}».\n\n"
        f"<blockquote expandable>{text}</blockquote>",
        parse_mode="HTML"
    )


async def setevent_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.effective_message
    chat = update.effective_chat

    if not await _check_admin(update, context):
        return

    parts = re.split(r"\s+", message.text, maxsplit=3)

    if len(parts) < 4:
        await message.reply_text(
            "Используй: /setevent название время текст\n"
            "Например: /setevent radio 23:00 <новый текст радио>"
        )
        return

    _, name, time_str, text = parts

    if not TIME_RE.match(time_str):
        await message.reply_text(
            "Неверный формат времени. Используй формат ЧЧ:ММ, "
            "например 20:00"
        )
        return

    name = name.lower()

    if name not in get_chat_events(chat.id):
        await message.reply_text(
            f"Событие «{escape(name)}» не найдено. Используй "
            "/addevent, чтобы создать новое."
        )
        return

    schedule_event(chat.id, name, time_str, text)

    try:
        await message.delete()
    except Exception:
        pass

    await chat.send_message(
        f"Изменён ивент «{escape(name)}».\n"
        f"Час: «{time_str}».\n\n"
        f"<blockquote expandable>{text}</blockquote>",
        parse_mode="HTML"
    )


async def delevent_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.effective_message
    chat = update.effective_chat

    if not await _check_admin(update, context):
        return

    if not context.args:
        await message.reply_text("Используй: /delevent название")
        return

    name = context.args[0].lower()

    # Забираем время/текст ДО удаления — remove_event стирает их из
    # хранилища, а подтверждение должно показать, что именно удалили.
    event = get_chat_events(chat.id).get(name)

    if event is None or not remove_event(chat.id, name):
        await message.reply_text(f"Событие «{escape(name)}» не найдено.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    await chat.send_message(
        f"Удалён ивент «{escape(name)}».\n"
        f"Час: «{event['time']}».\n\n"
        f"<blockquote expandable>{event['text']}</blockquote>",
        parse_mode="HTML"
    )


async def events_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.effective_message
    chat = update.effective_chat

    events = get_chat_events(chat.id)

    if not events:
        await message.reply_text("В этом чате пока нет событий.")
        return

    lines = ["<b>События этого чата:</b>"]

    for name, event in sorted(events.items()):
        preview = event["text"].splitlines()[0][:60]

        lines.append(
            f"• <b>{escape(name)}</b> — {event['time']} — "
            f"{escape(preview)}…"
        )

    try:
        await message.delete()
    except Exception:
        pass

    await chat.send_message(
        "\n".join(lines),
        parse_mode="HTML"
    )


async def on_bot_added_to_chat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_member_update = update.my_chat_member

    if chat_member_update is None:
        return

    old_status = chat_member_update.old_chat_member.status
    new_status = chat_member_update.new_chat_member.status

    was_out = old_status in ("left", "kicked")
    is_in = new_status in ("member", "administrator")

    if was_out and is_in:
        # Заводим 3 базовых события сразу, чтобы новый чат получил их
        # "из коробки", без ожидания первого /addevent.
        get_chat_events(chat_member_update.chat.id)

        print(
            "EVENTS: бот добавлен в чат "
            f"{chat_member_update.chat.id}, посеяны базовые события"
        )
