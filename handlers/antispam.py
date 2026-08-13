import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import ContextTypes

from handlers.antispam_storage import (
    get_burst_settings,
    get_repeat_settings,
    set_burst_settings,
    set_repeat_settings
)
from handlers.mute import MUTE_PERMISSIONS
from handlers.storage import add_warn
from utils.duration import parse_duration_seconds
from utils.permissions import is_chat_admin, require_admin


# (chat_id, user_id) -> deque[(timestamp, text_or_none, is_sticker_or_gif)].
# Только в памяти процесса — это защита от флуда в реальном времени,
# хранить историю сообщений на диске смысла нет.
_history = defaultdict(deque)


def _format_seconds(seconds):
    # Обратное превращение секунд в компактную строку для сообщений/логов,
    # например 120 -> "2m", 90 -> "90s".
    if seconds % (86400 * 365) == 0:
        return f"{seconds // (86400 * 365)}y"

    if seconds % 86400 == 0:
        return f"{seconds // 86400}d"

    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"

    if seconds % 60 == 0:
        return f"{seconds // 60}m"

    return f"{seconds}s"


def _describe_user(user):
    if user.username:
        return f"@{user.username} [{user.id}]"

    return f"{user.first_name} [{user.id}]"


def _describe_chat(chat):
    title = chat.title or chat.first_name or str(chat.id)
    return f"«{title}» ({chat.id})"


def _prune(entries, now, max_window):
    while entries and now - entries[0][0] > max_window:
        entries.popleft()


async def _punish(context, chat, user, minutes, warn, reason):
    until_date = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    who = _describe_user(user)
    where = _describe_chat(chat)

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=user.id,
            permissions=MUTE_PERMISSIONS,
            until_date=until_date
        )
    except Exception as e:
        print(
            f"ANTISPAM ERROR: не удалось замутить {who} в {where} | "
            f"{repr(e)}"
        )
        return

    if warn:
        add_warn(chat.id, user.id)

    try:
        await chat.send_message(
            f"🔇 {who} замучен на {minutes} мин. за {reason}."
        )
    except Exception as e:
        print(
            f"ANTISPAM ERROR: не удалось отправить уведомление в "
            f"{where} | {repr(e)}"
        )

    print(
        f"ANTISPAM: сработало в {where} | {who} | причина: {reason} | "
        f"мут: {minutes}м" + (" | + предупреждение" if warn else "")
    )


async def _handle_violation(
    context, chat, user, is_admin, minutes, warn, reason
):
    who = _describe_user(user)
    where = _describe_chat(chat)

    if is_admin:
        print(
            f"ANTISPAM: сработало бы в {where} | {who} | причина: "
            f"{reason} | пропущено, так как это админ"
        )
        return

    await _punish(context, chat, user, minutes, warn, reason)


async def check_spam(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if message is None or user is None or user.is_bot:
        return

    if chat.type not in ("group", "supergroup"):
        return

    burst = get_burst_settings(chat.id)
    repeat = get_repeat_settings(chat.id)

    if not burst["enabled"] and not repeat["enabled"]:
        return

    is_admin = await is_chat_admin(update, context)

    now = time.monotonic()
    key = (chat.id, user.id)
    entries = _history[key]

    is_sticker_or_gif = bool(message.sticker or message.animation)
    text = (message.text or message.caption or "").strip() or None

    entries.append((now, text, is_sticker_or_gif))

    max_window = max(burst["window"], repeat["window"])
    _prune(entries, now, max_window)

    # ===== Правило "антиспам": N+ сообщений за окно времени =====

    if burst["enabled"]:
        burst_count = sum(
            1 for ts, _, _ in entries if now - ts <= burst["window"]
        )

        if burst_count >= burst["limit"]:
            entries.clear()
            await _handle_violation(
                context, chat, user, is_admin,
                minutes=1, warn=True,
                reason=(
                    f"флуд ({burst_count} сообщ. за "
                    f"{_format_seconds(burst['window'])})"
                )
            )
            return

    # ===== Правило "антиповтор": N+ одинаковых сообщений либо =====
    # ===== стикеров/гифок за окно времени =====

    if repeat["enabled"]:
        recent = [
            (t, m) for ts, t, m in entries if now - ts <= repeat["window"]
        ]

        media_count = sum(1 for _, m in recent if m)

        if media_count >= repeat["limit"]:
            entries.clear()
            await _handle_violation(
                context, chat, user, is_admin,
                minutes=10, warn=False,
                reason=(
                    f"повтор стикеров/гифок ({media_count} за "
                    f"{_format_seconds(repeat['window'])})"
                )
            )
            return

        if text is not None:
            same_text_count = sum(1 for t, _ in recent if t == text)

            if same_text_count >= repeat["limit"]:
                entries.clear()
                await _handle_violation(
                    context, chat, user, is_admin,
                    minutes=10, warn=False,
                    reason=(
                        f"повтор сообщений ({same_text_count} за "
                        f"{_format_seconds(repeat['window'])})"
                    )
                )


def _format_rule_status(name, settings):
    if not settings["enabled"]:
        return f"{name}: выключен"

    return (
        f"{name}: {settings['limit']}+ за "
        f"{_format_seconds(settings['window'])}"
    )


async def _configure_rule(
    update,
    context,
    get_settings,
    set_settings,
    command_name,
    rule_label,
    mute_minutes,
    also_warns,
    example_extra
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

    usage = (
        f"Используй: /{command_name} <время> <кол-во> или "
        f"/{command_name} off\n"
        f"Например: /{command_name} 2s 5 — {example_extra}\n\n"
        f"Сейчас: {_format_rule_status(rule_label, get_settings(chat.id))}"
    )

    if not args:
        await chat.send_message(usage)
        return

    if args[0].lower() == "off":
        set_settings(chat.id, enabled=False)
        await chat.send_message(f"🔇 {rule_label} выключен для этого чата.")
        return

    if len(args) < 2:
        await chat.send_message(usage)
        return

    seconds = parse_duration_seconds(args[0])
    limit_text = args[1]

    if seconds is None or not limit_text.isdigit() or int(limit_text) <= 0:
        await chat.send_message(usage)
        return

    limit = int(limit_text)

    set_settings(chat.id, enabled=True, window=seconds, limit=limit)

    await chat.send_message(
        f"✅ {rule_label} включён: {limit}+ за {_format_seconds(seconds)} "
        f"-> мут {mute_minutes} мин."
        + (" + предупреждение" if also_warns else "")
    )


async def antispam_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await _configure_rule(
        update,
        context,
        get_burst_settings,
        set_burst_settings,
        command_name="antispam",
        rule_label="Antispam (флуд)",
        mute_minutes=1,
        also_warns=True,
        example_extra="10+ сообщений за 5 секунд"
    )


async def antirepeat_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await _configure_rule(
        update,
        context,
        get_repeat_settings,
        set_repeat_settings,
        command_name="antirepeat",
        rule_label="Antirepeat (повторы)",
        mute_minutes=10,
        also_warns=False,
        example_extra="10+ одинаковых сообщений/стикеров/гифок за 5 секунд"
    )
