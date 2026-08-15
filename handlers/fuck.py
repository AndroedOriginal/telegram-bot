import asyncio
import json
import random
from datetime import datetime, timedelta, timezone

from telegram import Update, ChatPermissions
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

from handlers.mute import MUTE_PERMISSIONS
from handlers.fuck_storage import (
    is_fuck_enabled,
    set_fuck_enabled,
    set_fuck_disabled,
)
from handlers.immunity_storage import is_immune
from utils.targeting import resolve_target
from utils.duration import parse_duration_seconds
from utils.paths import data_path


PLOTS_FILE = data_path("fuck_plots.json")

# Небольшая случайная пауза между сообщениями "постановки" — чтобы они
# не прилетали одним пакетом, а выглядели так, будто их печатают по ходу.
_MIN_DELAY = 1.2
_MAX_DELAY = 2.4


def _load_plots():
    try:
        with open(PLOTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("plots", [])
    except Exception as e:
        print(f"FUCK PLOTS LOAD ERROR: {repr(e)}")
        return []


def _is_creator(user_id, admins):
    return any(
        admin.user.id == user_id and admin.status == ChatMemberStatus.OWNER
        for admin in admins
    )


async def fuck_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.message
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ("group", "supergroup"):
        return

    admins = await context.bot.get_chat_administrators(chat.id)
    admin_ids = [admin.user.id for admin in admins]
    is_admin = user.id in admin_ids

    args = list(context.args) if context.args else []

    try:
        await message.delete()
    except Exception:
        pass

    # =========================
    # ВКЛ/ВЫКЛ — ТОЛЬКО ВЛАДЕЛЕЦ ЧАТА
    # =========================

    if args and args[0].lower() in ("on", "off"):
        if not _is_creator(user.id, admins):
            return

        if args[0].lower() == "off":
            set_fuck_disabled(chat.id)
            await chat.send_message("Команда «fuck» выключена в этом чате.")
            return

        until = None
        phrase = "навсегда"

        if len(args) > 1:
            seconds = parse_duration_seconds(args[1].lower())

            if seconds is None:
                await chat.send_message(
                    "Неверный формат времени. Примеры: 30s, 1m, 2h, 1d"
                )
                return

            until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
            phrase = f"на {args[1].lower()}"

        set_fuck_enabled(chat.id, until)

        await chat.send_message(
            f"Команда «fuck» включена в этом чате {phrase}."
        )
        return

    # =========================
    # САМА ШУТКА
    # =========================

    if not is_fuck_enabled(chat.id):
        return

    target_id, display_name, _args, error = await resolve_target(
        update, context, admin_ids
    )

    if error:
        await chat.send_message(error)
        return

    if target_id == context.bot.id:
        return

    target_is_admin = target_id in admin_ids

    # Обычный участник не может использовать команду на админе,
    # админы могут использовать её друг на друге.
    if target_is_admin and not is_admin:
        await chat.send_message(
            "Обычный участник не может использовать эту команду "
            "на администраторе."
        )
        return

    # Иммунитет защищает от этой команды всегда, даже от админов.
    if is_immune(chat.id, target_id):
        who = f"@{display_name}" if display_name else str(target_id)

        await chat.send_message(
            f"У {who} есть иммунитет — эта команда на него не действует."
        )
        return

    plots = _load_plots()

    if not plots:
        await chat.send_message(
            "Не нашлось ни одного сценария для этой команды."
        )
        return

    plot = random.choice(plots)
    safety_seconds = int(len(plot) * (_MAX_DELAY + 1) + 15)

    mention = f"@{display_name}" if display_name else str(target_id)

    # Мут без какого-либо отдельного сообщения об этом — тихо, чтобы не
    # мешать жертве отвечать посреди "постановки". Команда уже удалена
    # выше, никакого отдельного анонса не отправляется — сразу идёт сам
    # сценарий.
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_id,
            permissions=MUTE_PERMISSIONS,
            until_date=(
                datetime.now(timezone.utc)
                + timedelta(seconds=safety_seconds)
            )
        )
    except Exception as e:
        print(f"FUCK MUTE ERROR: {target_id} | {repr(e)}")

    await asyncio.sleep(random.uniform(_MIN_DELAY, _MAX_DELAY))

    for line in plot:
        try:
            await chat.send_message(line.replace("{target}", mention))
        except Exception as e:
            print(f"FUCK SEND ERROR: {repr(e)}")

        await asyncio.sleep(random.uniform(_MIN_DELAY, _MAX_DELAY))

    # Размут тоже без сообщения — по той же причине.
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_id,
            permissions=ChatPermissions.all_permissions()
        )
    except Exception as e:
        print(f"FUCK UNMUTE ERROR: {target_id} | {repr(e)}")

    print(
        f"FUCK: {user.id} использовал команду на {target_id} "
        f"в чате {chat.id}"
    )
