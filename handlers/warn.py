from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from html import escape
from handlers.storage import add_warn, remove_warn
from datetime import timedelta
from telegram import ChatPermissions


async def warn_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

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

    if count >= 3:
    
        await update.effective_chat.restrict_member(
            user_id,
            permissions=ChatPermissions(
                can_send_messages=False
            ),
            until_date=timedelta(minutes=10)
        )
    
        remove_warn(user_id)

        print(f"{username} получил мут на 10 минут")
    
        return
    
    try:
        await message.delete()
    except:
        pass


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


    username = user.username or user.first_name
    
    username = escape(username)
    reason = escape(reason)
    
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


    data = query.data

    user_id = int(
        data.replace("cancel_warn_", "")
    )


    remove_warn(user_id)


    await query.message.delete()
