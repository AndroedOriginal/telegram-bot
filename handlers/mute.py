from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from datetime import datetime, timedelta, timezone

from utils.duration import parse_duration_seconds
from utils.targeting import resolve_target


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

    try:
        await message.delete()
    except Exception:
        pass

    # =========================
    # ОПРЕДЕЛЯЕМ ЦЕЛЬ: ОТВЕТ, @USERNAME ИЛИ ID
    # =========================

    user_id, _display_name, args, error = await resolve_target(
        update,
        context,
        admin_ids
    )

    if error:
        await chat.send_message(error)
        return

    # =========================
    # НЕЛЬЗЯ МУТИТЬ АДМИНОВ
    # =========================
    # Telegram всё равно отклонит restrict_chat_member для админа,
    # но раньше эта ошибка проглатывалась молча — команда как будто
    # "срабатывала", а мут не применялся.

    if user_id in admin_ids:
        await chat.send_message(
            "❌ Нельзя замутить администратора"
        )
        return

    # =========================
    # ВРЕМЯ МУТА
    # =========================

    until_date = None
    duration_text = "навсегда"

    if args:

        time_text = args[0].lower()

        seconds = parse_duration_seconds(time_text)

        if seconds is None:
            await chat.send_message(
                "Неверный формат времени. Примеры: 30s, 1m, 2h, 1d, 1y"
            )
            return

        # ВАЖНО:
        # Telegram нужен момент окончания,
        # а не timedelta.
        until_date = datetime.now(timezone.utc) + timedelta(seconds=seconds)

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
        await chat.send_message(
            "⚠️ Не удалось замутить пользователя"
        )
        return
