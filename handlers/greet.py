import re

from telegram import Update
from telegram.ext import ContextTypes

from utils.permissions import require_admin


# Прежний статичный текст приветствия из welcome.py — используется по
# умолчанию, пока админ не укажет свой текст после /greet.
DEFAULT_GREET = (
    "Добро пожаловать в Нюберг чат!\n\n"
    "Место, где ты можешь пообщаться на любые темы, поделиться хорошей "
    "музыкой и посоревноваться с другими участниками в играх.\n\n"
    "Не забудь прочитать "
    "<a href=\"https://telegra.ph/Pravila-Nyuberg-CHata-12-03-2\">"
    "правила</a> чата, перед началом общения, говорят, тут строгая "
    "модерация 👀"
)

# Заявки на вступление НЕ одобряются автоматически — они копятся тут
# (только в памяти процесса) и одобряются лишь когда админ вызывает
# /greet. chat_id -> множество user_id.
_pending_requests = {}

# Текст, которым бот приветствует новых участников в каждом чате.
# Обновляется через /greet и НЕ сохраняется на диск — это не команда
# кастомизации, а способ "впустить и поприветствовать прямо сейчас".
_greet_text = {}


async def greet_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    # /greet — это то, что реально впускает ожидающих в чат: одобряет все
    # скопившиеся заявки на вступление (используя указанный текст или
    # стандартный для приветствия) и удаляет команду. Если заявок нет —
    # просто сразу шлёт текст в чат.
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

    _greet_text[chat.id] = text

    pending = _pending_requests.pop(chat.id, None)

    if not pending:
        await chat.send_message(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        return

    for user_id in pending:
        try:
            await context.bot.approve_chat_join_request(chat.id, user_id)
        except Exception as e:
            print(
                "GREET ERROR: не удалось принять заявку "
                f"{user_id} | {repr(e)}"
            )


async def track_join_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    # Заявку НЕ одобряем сразу — бот не должен добавлять людей сам по
    # себе. Просто запоминаем её, чтобы её впустил /greet.
    request = update.chat_join_request

    if request is None:
        return

    _pending_requests.setdefault(request.chat.id, set()).add(
        request.from_user.id
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
    text = _greet_text.get(chat.id, DEFAULT_GREET)

    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"GREET ERROR: {chat.id} | {repr(e)}")
