from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions
)

from telegram.ext import ContextTypes

from html import escape
from datetime import timedelta

from handlers.storage import (
    add_warn,
    remove_warn,
    reset_warn
)


async def warn_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

    admins = await context.bot.get_chat_administrators(
        update.effective_chat.id
    )

    admin_ids = [
        admin.user.id
        for admin in admins
    ]

    # Только администраторы могут использовать /warn
    if update.effective_user.id not in admin_ids:
        try:
            await message.delete()
        except:
            pass
        return

    # Команда должна быть ответом
    if not message.reply_to_message:
        await message.reply_text(
            "Используй команду ответом на сообщение пользователя:\n/warn причина"
        )
        return

    user = message.reply_to_message.from_user

    reason = " ".join(context.args)

    if not reason:
        reason = "Причина не указана"

    user_id = user.id

    count = add_warn(user_id)

    username = user.username or user.first_name

    username = escape(username)
    reason = escape(reason)

    try:
        await message.delete()
    except:
        pass

    # ====== 3 предупреждения -> мут ======

    if count >= 3:
        
        from datetime import datetime, timedelta
        
        until = datetime.now() + timedelta(minutes=10)
        
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_id,
            permissions=ChatPermissions(
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
            ),
            until_date=until
        )

        reset_warn(user_id)

        return

    # ====== обычное предупреждение ======

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

    await update.effective_chat.send_message(
        text=(
            f"@{username} [{user_id}] предупреждён ({count}/3).\n\n"
            f"<b>Причина:</b> {reason}"
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def cancel_warn(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = int(
        query.data.replace("cancel_warn_", "")
    )

    remove_warn(user_id)

    await query.message.delete()
