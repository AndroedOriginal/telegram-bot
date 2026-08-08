from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from datetime import datetime, timedelta, timezone
import re


async def mute_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message
    chat = update.effective_chat

    # =========================
    # ТОЛЬКО АДМИНИСТРАТОРЫ
    # =========================

    admins = await context.bot.get_chat_administrators(chat.id)
    admin_ids = [admin.user.id for admin in admins]

    if update.effective_user.id not in admin_ids:
        try:
            await message.delete()
        except Exception:
            pass
        return

    # =========================
    # КОМАНДА ДОЛЖНА БЫТЬ REPLY
    # =========================

    if not message.reply_to_message:
        try:
            await message.delete()
        except Exception:
            pass
        return

    user = message.reply_to_message.from_user
    user_id = user.id

    # =========================
    # ВРЕМЯ МУТА
    # =========================

    until_date = None
    duration_text = "навсегда"

    if context.args:

        time_text = context.args[0].lower()

        match = re.fullmatch(
            r"(\d+)(m|h|d)",
            time_text
        )

        if not match:
            try:
                await message.delete()
            except Exception:
                pass

            print(
                f"MUTE ERROR: неправильное время: {time_text}"
            )
            return

        value = int(match.group(1))
        unit = match.group(2)

        if unit == "m":
            duration = timedelta(minutes=value)

        elif unit == "h":
            duration = timedelta(hours=value)

        elif unit == "d":
            duration = timedelta(days=value)

        else:
            return

        # ВАЖНО:
        # Telegram нужен момент окончания,
        # а не timedelta.
        until_date = datetime.now(timezone.utc) + duration

        duration_text = time_text

    # =========================
    # МУТИМ
    # =========================

    try:

        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=user_id,

            permissions=ChatPermissions(
                can_send_messages=False
            ),

            until_date=until_date
        )

        print(
            f"MUTE: {user_id} | "
            f"время: {duration_text} | "
            f"до: {until_date}"
        )

    except Exception as e:

        print(
            f"MUTE ERROR: {user_id} | "
            f"{repr(e)}"
        )

    # =========================
    # УДАЛЯЕМ КОМАНДУ
    # =========================

    try:
        await message.delete()
    except Exception:
        pass
