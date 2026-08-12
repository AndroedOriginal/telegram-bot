import re
from html import escape

from telegram import Update
from telegram.ext import ContextTypes

from handlers.greet_storage import get_greet, set_greet, reset_greet
from utils.permissions import require_admin


def _mention(user):
    name = escape(user.full_name)
    return f'<a href="tg://user?id={user.id}">{name}</a>'


def _render(chat_id, mentions):
    text = get_greet(chat_id)

    if "{mention}" in text:
        return text.replace("{mention}", mentions)

    return text


async def greet_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.effective_message
    chat = update.effective_chat

    if not await require_admin(update, context):
        return

    parts = re.split(r"\s+", message.text, maxsplit=1)

    try:
        await message.delete()
    except Exception:
        pass

    if len(parts) < 2:
        # Без текста — сбрасываем на стандартное приветствие.
        reset_greet(chat.id)

        await chat.send_message(
            "Приветствие сброшено на стандартное.\n\n"
            f"<blockquote expandable>{get_greet(chat.id)}</blockquote>",
            parse_mode="HTML"
        )
        return

    text = parts[1]
    set_greet(chat.id, text)

    await chat.send_message(
        "Приветствие обновлено.\n\n"
        f"<blockquote expandable>{text}</blockquote>",
        parse_mode="HTML"
    )


async def greet_new_members(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    # Несколько людей могут быть добавлены одним системным сообщением —
    # шлём одно общее приветствие на всех, а не по одному на человека.
    message = update.effective_message

    if not message or not message.new_chat_members:
        return

    users = [u for u in message.new_chat_members if not u.is_bot]

    if not users:
        return

    chat = update.effective_chat
    mentions = ", ".join(_mention(u) for u in users)

    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=_render(chat.id, mentions),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"GREET ERROR: {chat.id} | {repr(e)}")


async def approve_join_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    request = update.chat_join_request

    if request is None:
        return

    chat = request.chat
    user = request.from_user

    try:
        await context.bot.approve_chat_join_request(chat.id, user.id)
    except Exception as e:
        print(f"GREET ERROR: не удалось принять заявку {user.id} | {repr(e)}")
        return

    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=_render(chat.id, _mention(user)),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"GREET ERROR: {chat.id} | {repr(e)}")
