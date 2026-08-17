from html import escape

from telegram import Update
from telegram.ext import ContextTypes

from utils.targeting import get_all_known_ids


# С запасом от лимита Telegram в 4096 символов на сообщение.
MAX_MESSAGE_LENGTH = 3500


def _mention(user):
    if user.username:
        return f"@{escape(user.username)}"

    return f'<a href="tg://user?id={user.id}">{escape(user.first_name)}</a>'


async def everyone_mention(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Реакция на "@everyone" где-либо в тексте сообщения (как @admins) —
    упоминает всех админов и всех обычных участников, которых бот
    знает по локальному справочнику (кто хоть раз писал в чат) и кто
    сейчас реально состоит в чате. Полного списка участников чата
    Bot API не даёт, поэтому это лучшее доступное приближение.
    """
    chat = update.effective_chat

    try:
        admins = await context.bot.get_chat_administrators(chat.id)
    except Exception:
        admins = []

    mentions = []
    seen_ids = set()

    for admin in admins:
        user = admin.user

        if user.is_bot:
            continue

        seen_ids.add(user.id)
        mentions.append(_mention(user))

    for user_id in get_all_known_ids():
        if user_id in seen_ids:
            continue

        try:
            member = await context.bot.get_chat_member(chat.id, user_id)
        except Exception:
            continue

        if member.status in ("left", "kicked") or member.user.is_bot:
            continue

        seen_ids.add(user_id)
        mentions.append(_mention(member.user))

    if not mentions:
        return

    header = "📢 <b>Общий сбор!</b>\n\n"
    chunks = []
    current = header

    for mention in mentions:
        addition = mention + " "

        if len(current) + len(addition) > MAX_MESSAGE_LENGTH:
            chunks.append(current.rstrip())
            current = ""

        current += addition

    if current.strip():
        chunks.append(current.rstrip())

    for part in chunks:
        await chat.send_message(part, parse_mode="HTML")
