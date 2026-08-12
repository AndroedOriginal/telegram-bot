from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions,
)
from telegram.ext import ContextTypes

from html import escape
from datetime import datetime, timedelta, timezone

from handlers.storage import (
    add_warn,
    remove_warn,
    reset_warn
)
from utils.targeting import resolve_target


async def warn_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message
    chat_id = update.effective_chat.id

    admins = await context.bot.get_chat_administrators(chat_id)

    admin_ids = [admin.user.id for admin in admins]

    if update.effective_user.id not in admin_ids:
        try:
            await message.delete()
        except:
            pass
        return

    user_id, display_name, args, error = await resolve_target(
        update,
        context,
        admin_ids
    )

    if error:
        await message.reply_text(error)
        return

    reason = " ".join(args)

    if not reason:
        reason = "Причина не указана"

    count = add_warn(chat_id, user_id)

    # Удаляем команду
    try:
        await message.delete()
    except:
        pass

    # ======= Третий варн =======

    if count >= 3:

        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=False
            ),
            # ВАЖНО: Telegram нужен момент окончания, а не timedelta.
            until_date=datetime.now(timezone.utc) + timedelta(minutes=10)
        )

        reset_warn(chat_id, user_id)

        return

    # ======= Первый и второй =======

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "❌ Отмена",
                    callback_data=f"cancel_warn_{user_id}"
                )
            ]
        ]
    )

    username = escape(display_name)
    reason = escape(reason)

    await update.effective_chat.send_message(
        text=(
            f"@{username} [{user_id}] предупреждён ({count}/3).\n\n"
            f"<b>Причина:</b> {reason}"
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def unwarn_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message
    chat_id = update.effective_chat.id

    admins = await context.bot.get_chat_administrators(chat_id)

    admin_ids = [admin.user.id for admin in admins]

    if update.effective_user.id not in admin_ids:
        try:
            await message.delete()
        except:
            pass
        return

    user_id, display_name, _args, error = await resolve_target(
        update,
        context,
        admin_ids
    )

    if error:
        await message.reply_text(error)
        return

    count = remove_warn(chat_id, user_id)

    try:
        await message.delete()
    except:
        pass

    await update.effective_chat.send_message(
        text=(
            f"✅ Снято предупреждение с @{escape(display_name)} "
            f"[{user_id}] ({count}/3)."
        )
    )


async def cancel_warn(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    chat_id = update.effective_chat.id

    # Проверяем, является ли нажавший администратором
    admins = await context.bot.get_chat_administrators(chat_id)

    admin_ids = [admin.user.id for admin in admins]

    if update.effective_user.id not in admin_ids:
        await query.answer(
            "⚠️У вас нету разрешений для выполнения этого действия",
            show_alert=True
        )
        return

    await query.answer()

    data = query.data

    user_id = int(
        data.replace("cancel_warn_", "")
    )

    remove_warn(chat_id, user_id)

    await query.message.delete()
