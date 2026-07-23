from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


warnings = {}


async def warn_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

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


    warnings[user_id] = warnings.get(user_id, 0) + 1


    count = warnings[user_id]


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


    if user_id in warnings:
        warnings[user_id] -= 1

        if warnings[user_id] <= 0:
            del warnings[user_id]


    await query.message.delete()
