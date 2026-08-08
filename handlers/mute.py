from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from datetime import timedelta
import re


async def mute_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

    # Только админы
    admins = await context.bot.get_chat_administrators(
        update.effective_chat.id
    )

    admin_ids = [admin.user.id for admin in admins]

    if update.effective_user.id not in admin_ids:
        try:
            await message.delete()
        except:
            pass
        return

    # Команда должна быть ответом на сообщение
    if not message.reply_to_message:
        try:
            await message.delete()
        except:
            pass
        return

    user = message.reply_to_message.from_user
    user_id = user.id

    # По умолчанию — навсегда
    until_date = None

    # Если указано время
    if context.args:

        time_text = context.args[0].lower()

        match = re.fullmatch(
            r"(\d+)(m|h|d)",
            time_text
        )

        if not match:
            try:
                await message.delete()
            except:
                pass
            return

        value = int(match.group(1))
        unit = match.group(2)

        if unit == "m":
            until_date = timedelta(minutes=value)

        elif unit == "h":
            until_date = timedelta(hours=value)

        elif unit == "d":
            until_date = timedelta(days=value)

    # Выдаём мут
    await context.bot.restrict_chat_member(
        chat_id=update.effective_chat.id,
        user_id=user_id,
        permissions=ChatPermissions(
            can_send_messages=False
        ),
        until_date=until_date
    )

    # Удаляем команду
    try:
        await message.delete()
    except:
        pass

    print(
        f"MUTE: {user_id} | "
        f"время: {'навсегда' if until_date is None else context.args[0]}"
    )uration}"
    )
