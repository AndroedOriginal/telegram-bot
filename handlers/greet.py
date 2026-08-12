import re

from telegram import Update
from telegram.ext import ContextTypes

from utils.permissions import require_admin


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
    # Только принимаем заявку. Приветствие сюда не относится — оно всегда
    # реагирует на СЛУЖЕБНОЕ сообщение "X присоединился", которое Telegram
    # публикует в чат после вступления (см. greet_new_members). Так порядок
    # гарантированно правильный: сначала виден вход, потом приветствие —
    # даже если заявку одобрил сам админ вручную из Telegram.
    request = update.chat_join_request

    if request is None:
        return

    try:
        await context.bot.approve_chat_join_request(
            request.chat.id,
            request.from_user.id
        )
    except Exception as e:
        print(
            "GREET ERROR: не удалось принять заявку "
            f"{request.from_user.id} | {repr(e)}"
        )


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

    users = [u for u in message.new_chat_members if not u.is_bot]

    if not users:
        return

    chat = update.effective_chat

    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=DEFAULT_GREET,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"GREET ERROR: {chat.id} | {repr(e)}")
