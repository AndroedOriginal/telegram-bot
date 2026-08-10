from telegram import Update
from telegram.ext import ContextTypes


async def msg_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

    # Проверка администратора
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


    # Если текста нет
    if not context.args:
        try:
            await message.delete()
        except:
            pass
        return


    text = " ".join(context.args)

    # Если /send использован ответом на сообщение — отвечаем на него же
    reply_to_id = None

    if message.reply_to_message:
        reply_to_id = message.reply_to_message.message_id


    # Удаляем команду
    try:
        await message.delete()
    except:
        pass


    # Отправляем сообщение от имени бота
    await update.effective_chat.send_message(
        text=text,
        reply_to_message_id=reply_to_id,
        allow_sending_without_reply=True
    )

    print(
        f"MSG от {update.effective_user.id}: {text}"
    )
