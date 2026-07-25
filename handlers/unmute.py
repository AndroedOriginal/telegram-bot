from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes


async def unmute_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

    # Проверяем администратора
    admins = await context.bot.get_chat_administrators(
        update.effective_chat.id
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


    # Проверяем ответ
    if not message.reply_to_message:

        try:
            await message.delete()
        except:
            pass

        print("UNMUTE ERROR: no reply")
        return


    user = message.reply_to_message.from_user


    # Снимаем ограничения
    await context.bot.restrict_chat_member(
        chat_id=update.effective_chat.id,
        user_id=user.id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
    )


    # Удаляем команду
    try:
        await message.delete()
    except:
        pass


    print(
        f"UNMUTE: {user.username or user.first_name} ({user.id})"
    )
