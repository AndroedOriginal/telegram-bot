from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes

from html import escape
from datetime import datetime, timedelta, timezone

from utils.targeting import resolve_target
from utils.duration import parse_duration_seconds
from handlers.immunity_storage import set_immunity, remove_immunity


# Декоративный значок иммунитета в теге участника. НЕ используется нигде
# для проверки самого иммунитета (см. immunity_storage.is_immune) — тег
# может быть потерян/изменён вручную, это чистая косметика.
IMMUNITY_ICON = "⛨"
MAX_TAG_LENGTH = 16


async def _update_tag(context, chat_id, user_id, granting):
    """
    Добавляет/убирает значок иммунитета в конце тега участника.
    Если тега не было — при выдаче ставится сам значок. Если места не
    хватает (лимит Telegram — 16 символов) либо API отклонило запрос
    (нет прав can_manage_tags, символ недопустим и т.п.) — шаг тега
    молча пропускается, а вызывающий код показывает предупреждение
    в чате. Сам иммунитет при этом уже выдан/снят и не зависит от тега.
    """
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
    except Exception as e:
        print(f"IMMUNITY TAG ERROR (get_chat_member): {user_id} | {repr(e)}")
        return "⚠️ Не удалось прочитать текущий тег участника — тег не изменён."

    current_tag = getattr(member, "tag", None) or ""

    if granting:
        if not current_tag:
            new_tag = IMMUNITY_ICON
        elif current_tag.endswith(IMMUNITY_ICON):
            return None

        else:
            candidate = f"{current_tag} {IMMUNITY_ICON}"

            if len(candidate) > MAX_TAG_LENGTH:
                return (
                    "⚠️ В теге участника не хватает места для значка "
                    f"иммунитета {IMMUNITY_ICON} — иммунитет всё равно "
                    "выдан, тег не изменён."
                )

            new_tag = candidate

    else:
        if not current_tag:
            return None

        if current_tag == IMMUNITY_ICON:
            new_tag = ""
        elif current_tag.endswith(f" {IMMUNITY_ICON}"):
            new_tag = current_tag[: -len(f" {IMMUNITY_ICON}")]
        elif current_tag.endswith(IMMUNITY_ICON):
            new_tag = current_tag[: -len(IMMUNITY_ICON)]
        else:
            return None

    try:
        await context.bot.set_chat_member_tag(
            chat_id=chat_id,
            user_id=user_id,
            tag=new_tag
        )
    except Exception as e:
        print(f"IMMUNITY TAG ERROR (set_chat_member_tag): {user_id} | {repr(e)}")

        if granting:
            return (
                "⚠️ Не удалось обновить тег участника (нет прав или "
                "символ недопустим) — иммунитет всё равно выдан."
            )

        return "⚠️ Не удалось убрать значок иммунитета из тега участника."

    return None


async def immunity_command(
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

    username = escape(display_name or str(user_id))

    if user_id == context.bot.id:
        return

    # =========================
    # АДМИНАМ ИММУНИТЕТ НЕ НУЖЕН — У НИХ УЖЕ ЕСТЬ ВСЕ ПРАВА
    # =========================

    if user_id in admin_ids:
        await chat.send_message(
            f"❌ @{username} [{user_id}] — администратор, иммунитет "
            "ему не нужен."
        )
        return

    # =========================
    # СНЯТИЕ ИММУНИТЕТА
    # =========================

    if args and args[0].lower() == "off":
        remove_immunity(chat.id, user_id)

        tag_warning = await _update_tag(
            context, chat.id, user_id, granting=False
        )

        await chat.send_message(
            f"Иммунитет снят с @{username} [{user_id}]."
        )

        if tag_warning:
            await chat.send_message(tag_warning)

        return

    # =========================
    # ВЫДАЧА ИММУНИТЕТА
    # =========================

    until = None
    phrase = "навсегда"

    if args:
        time_text = args[0].lower()
        seconds = parse_duration_seconds(time_text)

        if seconds is None:
            await chat.send_message(
                "Неверный формат времени. Примеры: 30s, 1m, 2h, 1d, 1y. "
                "Либо укажи «off», чтобы снять иммунитет."
            )
            return

        until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        phrase = f"на {time_text}"

    set_immunity(chat.id, user_id, until)

    print(
        f"IMMUNITY GRANTED: {user_id} в чате {chat.id} | "
        f"до: {until if until else 'навсегда'}"
    )

    tag_warning = await _update_tag(
        context, chat.id, user_id, granting=True
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "❌ Отмена",
                    callback_data=f"cancel_immunity_{user_id}"
                )
            ]
        ]
    )

    await chat.send_message(
        f"@{username} [{user_id}] получил(а) иммунитет {phrase}.",
        reply_markup=keyboard
    )

    if tag_warning:
        await chat.send_message(tag_warning)


async def cancel_immunity_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    chat_id = update.effective_chat.id

    # Кнопка отмены видна всем, но действует только для админов —
    # как и остальные admin-only кнопки бота (cancel_warn, unban).
    admins = await context.bot.get_chat_administrators(chat_id)
    admin_ids = [admin.user.id for admin in admins]

    if update.effective_user.id not in admin_ids:
        await query.answer(
            "⚠️У вас нету разрешений для выполнения этого действия",
            show_alert=True
        )
        return

    await query.answer()

    user_id = int(query.data.replace("cancel_immunity_", ""))

    remove_immunity(chat_id, user_id)

    await _update_tag(context, chat_id, user_id, granting=False)

    await query.message.delete()
