from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import ContextTypes
from html import escape


async def ban_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.message
    chat = update.effective_chat

    # проверка админа
    admins = await context.bot.get_chat_administrators(
        chat.id
    )

    admin_ids = [
        admin.user.id
        for admin in admins
    ]

    if update.effective_user.id not in admin_ids:
        try:
            await message.delete()
        except:
            pass
        return

    # нужен ответ на сообщение
    if not message.reply_to_message:
        await message.reply_text(
            "Используй /ban ответом на сообщение пользователя"
        )
        return

    target = message.reply_to_message.from_user

    # нельзя банить админов
    if target.id in admin_ids:
        await message.delete()

        await message.reply_text(
            "❌ Нельзя заблокировать администратора"
        )
        return

    reason = " ".join(context.args)

    if not reason:
        reason = "Причина не указана"

    username = escape(
        target.username or target.first_name
    )

    # бан
    await context.bot.ban_chat_member(
        chat_id=chat.id,
        user_id=target.id
    )

    # удаляем команду
    try:
        await message.delete()
    except:
        pass

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Разблокировать",
                    callback_data=f"unban_{target.id}"
                )
            ]
        ]
    )

    await chat.send_message(
        text=(
            f"@{username} [{target.id}] "
            "заблокирован(а).\n\n"
            f"<b>Причина:</b> {escape(reason)}"
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def unban_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    # Проверяем права
    admins = await context.bot.get_chat_administrators(
        update.effective_chat.id
    )

    admin_ids = [admin.user.id for admin in admins]

    if update.effective_user.id not in admin_ids:
        await query.answer(
            "⚠️У вас нету разрешений для выполнения этого действия",
            show_alert=True
        )
        return

    await query.answer()

    # Остальной код снятия бана
    data = query.data

    user_id = int(
        data.replace("unban_", "")
    )

    await context.bot.unban_chat_member(
        chat_id=update.effective_chat.id,
        user_id=user_id
    )

    await query.message.delete()
