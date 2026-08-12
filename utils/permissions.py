async def is_chat_admin(update, context):
    chat = update.effective_chat
    admins = await context.bot.get_chat_administrators(chat.id)
    admin_ids = [admin.user.id for admin in admins]

    return update.effective_user.id in admin_ids


async def require_admin(update, context):
    """
    Возвращает True, если автор сообщения — админ чата. Если нет —
    молча удаляет команду (если получится) и возвращает False.
    """
    if await is_chat_admin(update, context):
        return True

    try:
        await update.effective_message.delete()
    except Exception:
        pass

    return False
