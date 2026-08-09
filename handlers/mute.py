from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from datetime import datetime, timedelta, timezone
import re


# Явно выключаем ВСЕ права, а не только отправку текста —
# иначе замученный всё ещё может слать стикеры/медиа/опросы.
MUTE_PERMISSIONS = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False
)


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
        await message.reply_text(
            "Используй /mute ответом на сообщение пользователя"
        )
        return

    user = message.reply_to_message.from_user
    user_id = user.id

    # =========================
    # НЕЛЬЗЯ МУТИТЬ АДМИНОВ
    # =========================
    # Telegram всё равно отклонит restrict_chat_member для админа,
    # но раньше эта ошибка проглатывалась молча — команда как будто
    # "срабатывала", а мут не применялся.

    if user_id in admin_ids:
        try:
            await message.delete()
        except Exception:
            pass

        await message.reply_text(
            "❌ Нельзя замутить администратора"
        )
        return

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

        if not match or int(match.group(1)) <= 0:
            await message.reply_text(
                "Неверный формат времени. Примеры: 1m, 2h, 1d"
            )
            return

        value = int(match.group(1))
        unit = match.group(2)

        if unit == "m":
            duration = timedelta(minutes=value)

        elif unit == "h":
            duration = timedelta(hours=value)

        else:
            duration = timedelta(days=value)

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
            permissions=MUTE_PERMISSIONS,
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

        # Раньше ошибка ничем не выдавалась — мут молча не срабатывал.
        await message.reply_text(
            "⚠️ Не удалось замутить пользователя"
        )
        return

    # =========================
    # УДАЛЯЕМ КОМАНДУ
    # =========================

    try:
        await message.delete()
    except Exception:
        pass
