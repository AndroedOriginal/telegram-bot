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
from utils.permissions import require_admin


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


async def addevent_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    # update.message пустой для отредактированных сообщений — команда,
    # присланная правкой уже отправленного текста, иначе рушила хендлер.
    message = update.effective_message
    chat = update.effective_chat

    if not await require_admin(update, context):
        return

    # re.split с maxsplit сохраняет пробелы/переносы строк/спойлеры
    # в тексте события без изменений.
    parts = re.split(r"\s+", message.text, maxsplit=3)

    try:
        await message.delete()
    except Exception:
        pass

    if len(parts) < 4:
        await chat.send_message(
            "Используй: /addevent название время текст\n"
            "Например: /addevent movie 20:00 Сегодня смотрим фильм!"
        )
        return

    _, name, time_str, text = parts

    if not NAME_RE.match(name):
        await chat.send_message(
            "Название события может содержать только буквы, цифры, "
            "_ и -, без пробелов."
        )
        return

    if not TIME_RE.match(time_str):
        await chat.send_message(
            "Неверный формат времени. Используй формат ЧЧ:ММ, "
            "например 20:00"
        )
        return

    name = name.lower()

    if name in get_chat_events(chat.id):
        await chat.send_message(
            f"Событие «{escape(name)}» уже существует. Используй "
            "/setevent, чтобы изменить его."
        )
        return

    schedule_event(chat.id, name, time_str, text)

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

    if not await require_admin(update, context):
        return

    parts = re.split(r"\s+", message.text, maxsplit=3)

    try:
        await message.delete()
    except Exception:
        pass

    if len(parts) < 4:
        await chat.send_message(
            "Используй: /setevent название время текст\n"
            "Например: /setevent radio 23:00 <новый текст радио>"
        )
        return

    _, name, time_str, text = parts

    if not TIME_RE.match(time_str):
        await chat.send_message(
            "Неверный формат времени. Используй формат ЧЧ:ММ, "
            "например 20:00"
        )
        return

    name = name.lower()

    if name not in get_chat_events(chat.id):
        await chat.send_message(
            f"Событие «{escape(name)}» не найдено. Используй "
            "/addevent, чтобы создать новое."
        )
        return

    schedule_event(chat.id, name, time_str, text)

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

    if not await require_admin(update, context):
        return

    args = context.args

    try:
        await message.delete()
    except Exception:
        pass

    if not args:
        await chat.send_message("Используй: /delevent название")
        return

    name = args[0].lower()

    # Забираем время/текст ДО удаления — remove_event стирает их из
    # хранилища, а подтверждение должно показать, что именно удалили.
    event = get_chat_events(chat.id).get(name)

    if event is None or not remove_event(chat.id, name):
        await chat.send_message(f"Событие «{escape(name)}» не найдено.")
        return

    await chat.send_message(
        f"Удалён ивент «{escape(name)}».\n"
        f"Час: «{event['time']}».\n\n"
        f"<blockquote expandable>{event['text']}</blockquote>",
        parse_mode="HTML"
    )


async def launchevent_command(
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

    if not args:
        await chat.send_message("Используй: /launchevent название")
        return

    name = args[0].lower()
    event = get_chat_events(chat.id).get(name)

    if event is None:
        await chat.send_message(f"Событие «{escape(name)}» не найдено.")
        return

    await _send_event(_resolve_chat_id(chat.id), event["text"])


async def events_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    # В отличие от остальных команд этого модуля, /events доступна
    # любому пользователю чата, а не только админам — это просмотр
    # расписания, а не его изменение.
    message = update.effective_message
    chat = update.effective_chat

    events = get_chat_events(chat.id)

    try:
        await message.delete()
    except Exception:
        pass

    if not events:
        await chat.send_message("В этом чате пока нет событий.")
        return

    blocks = ["<b>События этого чата:</b>"]

    for name, event in sorted(events.items()):
        blocks.append(
            f"<tg-spoiler>{escape(name)}</tg-spoiler>\n"
            f"Час: «{event['time']}».\n\n"
            f"<blockquote expandable>{event['text']}</blockquote>"
        )

    await chat.send_message(
        "\n\n".join(blocks),
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
