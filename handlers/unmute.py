from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes

from utils.targeting import resolve_target


async def unmute_command(
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

    # Определяем цель: ответом, по @username или по ID
    user_id, display_name, _args, error = await resolve_target(
        update,
        context,
        admin_ids
    )

    if error:
        await message.reply_text(error)
        return

    # Снятие мута.
    # Восстанавливаем ВСЕ права, а не только текст — mute_command
    # отключает их все, иначе часть ограничений осталась бы навсегда.
    await context.bot.restrict_chat_member(
        chat_id=update.effective_chat.id,
        user_id=user_id,
        permissions=ChatPermissions.all_permissions()
    )

    # Удаляем команду
    try:
        await message.delete()
    except:
        pass

    print(
        f"UNMUTE: {display_name} ({user_id})"
    )
