import asyncio
from datetime import datetime, timedelta, timezone

import pytz

from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes

from utils.duration import parse_duration_seconds
from utils.targeting import resolve_target
from handlers.mute import MUTE_PERMISSIONS
from handlers.immunity_storage import is_immune
from handlers.fuck_storage import set_fuck_toggle, disable_fuck, is_fuck_enabled
from handlers.nudesday_storage import is_nudesday_enabled
from handlers.plots_storage import get_random_plot, get_plot


MOSCOW_TZ = pytz.timezone("Europe/Moscow")

# Пауза между сообщениями сценария: минимум 1 секунда, длиннее для
# длинных сообщений — чтобы выглядело, будто их печатают, а не шлют
# одним пакетом.
_BASE_DELAY = 1.0
_CHARS_PER_SECOND = 20

# Плейсхолдер, который в тексте сценария подменяется на реальное
# упоминание жертвы (например "мы предупреждали тебя, @username").
_MENTION_PLACEHOLDER = "@username"


def _delay_for(text):
    return max(_BASE_DELAY, len(text) / _CHARS_PER_SECOND)


def _is_thursday_now():
    return datetime.now(MOSCOW_TZ).weekday() == 3


async def _run_joke(context, chat_id, user_id, plot=None):
    """
    Мутит цель, шлёт сценарий сообщение за сообщением с небольшой
    паузой, потом снимает мут. Всё без единого служебного сообщения
    от бота о муте/размуте — это часть шутки, а не модерации.
    """
    if plot is None:
        plot = get_random_plot()

    if not plot:
        print("FUCK: библиотека сценариев пуста — /addplot, чтобы добавить")
        return

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        target_user = member.user
        mention = (
            f"@{target_user.username}"
            if target_user.username
            else target_user.first_name
        )
    except Exception as e:
        print(f"FUCK MENTION ERROR: {user_id} | {repr(e)}")
        mention = str(user_id)

    lines = [line.replace(_MENTION_PLACEHOLDER, mention) for line in plot]

    # На случай, если бот упадёт/перезапустится посреди сценария — мут
    # снимется сам по истечении разумного запаса времени, а не останется
    # навсегда. Обычно же ниже мы снимаем его вручную сразу после
    # последнего сообщения.
    safety_seconds = int(sum(_delay_for(line) for line in lines)) + 15
    until_date = datetime.now(timezone.utc) + timedelta(seconds=safety_seconds)

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=MUTE_PERMISSIONS,
            until_date=until_date
        )
    except Exception as e:
        print(f"FUCK MUTE ERROR: {user_id} | {repr(e)}")
        return

    print(f"FUCK: {user_id} в чате {chat_id} | сценарий из {len(lines)} сообщ.")

    for line in lines:
        try:
            await context.bot.send_message(chat_id=chat_id, text=line)
        except Exception as e:
            print(f"FUCK SEND ERROR: {chat_id} | {repr(e)}")

        await asyncio.sleep(_delay_for(line))

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions.all_permissions()
        )
    except Exception as e:
        print(f"FUCK UNMUTE ERROR: {user_id} | {repr(e)}")


async def fuck_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.effective_message
    chat = update.effective_chat
    actor = update.effective_user

    admins = await context.bot.get_chat_administrators(chat.id)
    admin_ids = [a.user.id for a in admins]
    owner_id = next(
        (a.user.id for a in admins if a.status == "creator"),
        None
    )

    args = list(context.args) if context.args else []

    # =========================================================
    # "fuck on" / "fuck off" — тумблер, доступен только владельцу чата
    # =========================================================

    if args and args[0].lower() in ("on", "off"):
        try:
            await message.delete()
        except Exception:
            pass

        if actor.id != owner_id:
            return

        if args[0].lower() == "off":
            disable_fuck(chat.id)
            await chat.send_message("/fuck выключен в этом чате.")
            return

        until = None
        phrase = "навсегда"

        if len(args) > 1:
            seconds = parse_duration_seconds(args[1].lower())

            if seconds is None:
                await chat.send_message(
                    "Неверный формат времени. Примеры: 30s, 1m, 2h, 1d, 1y"
                )
                return

            until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
            phrase = f"на {args[1].lower()}"

        set_fuck_toggle(chat.id, until)
        await chat.send_message(f"/fuck включён {phrase}.")
        return

    # =========================================================
    # Сама шутка
    # =========================================================

    try:
        await message.delete()
    except Exception:
        pass

    is_admin = actor.id in admin_ids

    # Доступ: если в чате включён нюдсочетверг — админы могут всегда,
    # обычные участники только по четвергам. Если нюдсочетверг выключен —
    # действует обычный тумблер /fuck (на/навсегда/выкл), одинаковый
    # для всех.
    if is_nudesday_enabled(chat.id):
        allowed = is_admin or _is_thursday_now()
    else:
        allowed = is_fuck_enabled(chat.id)

    if not allowed:
        return

    # resolve_target уже умеет брать цель из ответа на сообщение,
    # @username или ID — во всех трёх случаях "rest" содержит то, что
    # осталось после цели, т.е. необязательное имя сценария:
    # "/fuck @user plotname", "/fuck 12345 plotname" или ответом
    # "/fuck plotname".
    user_id, _display_name, rest, error = await resolve_target(
        update,
        context,
        admin_ids
    )

    if error:
        await chat.send_message(error)
        return

    if user_id == context.bot.id or user_id == actor.id:
        return

    # Обычные участники не могут применить команду на админов —
    # админы друг на друге могут.
    if not is_admin and user_id in admin_ids:
        return

    # Иммунитет защищает даже от админов.
    if is_immune(chat.id, user_id):
        return

    plot = None

    if rest:
        plot = get_plot(rest[0])

        if plot is None:
            await chat.send_message(f"Сценарий «{rest[0]}» не найден.")
            return

    context.application.create_task(
        _run_joke(context, chat.id, user_id, plot)
    )
