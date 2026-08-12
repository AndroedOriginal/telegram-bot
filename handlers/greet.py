import re
import time

from telegram import Update
from telegram.ext import ContextTypes

from utils.permissions import require_admin


# Заявки, одобренные самим ботом, не порождают в чате служебное сообщение
# "X присоединился" (в отличие от прямого добавления или заявки, одобренной
# вручную самим админом) — Telegram просто тихо делает пользователя
# участником. Поэтому только для этого пути шлём приветствие сами, сразу
# после одобрения. Отметка здесь не даёт greet_new_members продублировать
# приветствие, если служебное сообщение всё же придёт с запозданием.
_bot_approved = {}
_DEDUPE_WINDOW = 60


def _mark_bot_approved(chat_id, user_id):
    _bot_approved[(chat_id, user_id)] = time.monotonic()


def _was_bot_approved(chat_id, user_id):
    now = time.monotonic()

    for key, ts in list(_bot_approved.items()):
        if now - ts > _DEDUPE_WINDOW:
            del _bot_approved[key]

    return (chat_id, user_id) in _bot_approved


# Прежний статичный текст приветствия из welcome.py — используется
# автоматически при каждом вступлении, и как текст по умолчанию для /greet.
DEFAULT_GREET = (
    "Добро пожаловать в Нюберг чат!\n\n"
    "Место, где ты можешь пообщаться на любые темы, поделиться хорошей "
    "музыкой и посоревноваться с другими участниками в играх.\n\n"
    "Не забудь прочитать "
    "<a href=\"https://telegra.ph/Pravila-Nyuberg-CHata-12-03-2\">"
    "правила</a> чата, перед началом общения, говорят, тут строгая "
    "модерация 👀"
)


async def greet_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    # /greet не хранит и не настраивает приветствие — он просто сразу же
    # шлёт его в чат (тем же текстом, что уходит новым участникам
    # автоматически, либо своим, если он указан после команды).
    message = update.effective_message
    chat = update.effective_chat

    if not await require_admin(update, context):
        return

    parts = re.split(r"\s+", message.text, maxsplit=1)
    text = parts[1] if len(parts) > 1 else DEFAULT_GREET

    try:
        await message.delete()
    except Exception:
        pass

    await chat.send_message(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )


async def approve_join_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    # Одобряем заявку и сами же шлём приветствие — Telegram не публикует
    # "X присоединился" для заявок, одобренных ботом (в отличие от прямого
    # добавления или заявки, одобренной вручную самим админом, которые
    # ловит greet_new_members), так что ждать это сообщение здесь бессмысленно.
    request = update.chat_join_request

    if request is None:
        return

    chat = request.chat
    user = request.from_user

    try:
        await context.bot.approve_chat_join_request(chat.id, user.id)
    except Exception as e:
        print(
            "GREET ERROR: не удалось принять заявку "
            f"{user.id} | {repr(e)}"
        )
        return

    _mark_bot_approved(chat.id, user.id)

    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=DEFAULT_GREET,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"GREET ERROR: {chat.id} | {repr(e)}")


async def greet_new_members(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    # Несколько людей могут быть добавлены одним системным сообщением —
    # шлём одно общее приветствие на всех, а не по одному на человека.
    # Реагируем именно на это сообщение (а не на chat_member), чтобы
    # приветствие гарантированно шло ПОСЛЕ видимого "X присоединился".
    message = update.effective_message

    if not message or not message.new_chat_members:
        return

    chat = update.effective_chat

    users = [
        u for u in message.new_chat_members
        if not u.is_bot and not _was_bot_approved(chat.id, u.id)
    ]

    if not users:
        return

    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=DEFAULT_GREET,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"GREET ERROR: {chat.id} | {repr(e)}")
