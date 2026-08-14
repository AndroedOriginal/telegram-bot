import time

# Кэш списков админов чата — antispam проверяет права на КАЖДОЕ сообщение,
# и без кэша это означало бы отдельный запрос к Telegram на каждое
# сообщение в чате. TTL небольшой, чтобы смена админов подхватывалась
# быстро, но не мгновенно.
_ADMIN_CACHE_TTL = 60
_admin_cache = {}


async def _get_admin_ids(chat_id, context):
    cached = _admin_cache.get(chat_id)
    now = time.monotonic()

    if cached and now - cached[0] < _ADMIN_CACHE_TTL:
        return cached[1]

    admins = await context.bot.get_chat_administrators(chat_id)
    admin_ids = [admin.user.id for admin in admins]

    _admin_cache[chat_id] = (now, admin_ids)

    return admin_ids


async def is_chat_admin(update, context):
    chat = update.effective_chat
    admin_ids = await _get_admin_ids(chat.id, context)

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


async def on_chat_member_changed(update, context):
    """
    Сбрасывает кэш админов чата сразу при любом изменении прав участника —
    повышение, понижение, снятие ограничений, смена custom_title (тега
    рядом с ником) и т.п. Без этого только что назначенный админ или тот,
    кому только что дали тег, до _ADMIN_CACHE_TTL секунд считался бы
    обычным участником и мог попасть под antispam.
    """
    chat_member_update = update.chat_member

    if chat_member_update is None:
        return

    _admin_cache.pop(chat_member_update.chat.id, None)
