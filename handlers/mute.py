from telegram import (
    Update,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes
from html import escape
from datetime import datetime, timedelta, timezone

from utils.duration import parse_duration_seconds
from utils.targeting import resolve_target
from handlers.immunity_storage import is_immune


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

    user_id, display_name, args, error = await resolve_target(
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

    # иммунитет защищает от мута (но не от antispam/antirepeat)
    if is_immune(chat.id, user_id):
        await chat.send_message(
            f"У @{escape(display_name)} [{user_id}] есть иммунитет "
            "— замутить нельзя."
        )
        return

    # =========================
    # ВРЕМЯ И ПРИЧИНА
    # =========================
    # Формат теперь "/mute время причина" — первый аргумент, если это
    # распознаваемая длительность (30s, 1m, 2h, 1d, 1y), задаёт срок мута,
    # а всё, что после него, идёт в причину. Если первый аргумент не
    # похож на длительность, срок считается бессрочным, а весь текст
    # уходит в причину (как в /ban и /warn).

    until_date = None
    duration_text = "навсегда"
    reason_args = args

    if args:
        seconds = parse_duration_seconds(args[0].lower())

        if seconds is not None:
            # ВАЖНО: Telegram нужен момент окончания, а не timedelta.
            until_date = datetime.now(timezone.utc) + timedelta(seconds=seconds)
            duration_text = args[0].lower()
            reason_args = args[1:]

    reason = " ".join(reason_args)

    if not reason:
        reason = "Причина не указана"

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
            f"причина: {reason} | "
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

    # =========================
    # ПОДТВЕРЖДЕНИЕ + КНОПКА ОТМЕНЫ (только для админов)
    # =========================

    phrase = "навсегда" if duration_text == "навсегда" else f"на {duration_text}"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "❌ Отмена",
                    callback_data=f"cancel_mute_{user_id}"
                )
            ]
        ]
    )

    await chat.send_message(
        text=(
            f"@{escape(display_name)} [{user_id}] получил(а) мьют "
            f"{phrase}.\n\n"
            f"<b>Причина:</b> {escape(reason)}"
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def cancel_mute_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    chat_id = update.effective_chat.id

    admins = await context.bot.get_chat_administrators(chat_id)
    admin_ids = [admin.user.id for admin in admins]

    if update.effective_user.id not in admin_ids:
        await query.answer(
            "⚠️У вас нету разрешений для выполнения этого действия",
            show_alert=True
        )
        return

    await query.answer()

    user_id = int(query.data.replace("cancel_mute_", ""))

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions.all_permissions()
        )
    except Exception as e:
        print(f"CANCEL MUTE ERROR: {user_id} | {repr(e)}")

    await query.message.delete()
