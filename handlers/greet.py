import re

from telegram import Update, ChatMember
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
    # Только принимаем заявку — приветствие отправит
    # greet_on_membership_change, когда статус пользователя реально
    # поменяется на "участник" (что происходит и здесь, и если админ
    # одобрит заявку вручную из самого Telegram).
    request = update.chat_join_request

    if request is None:
        return

    print(
        "GREET: получена заявка на вступление "
        f"{request.from_user.id} в чат {request.chat.id}"
    )

    try:
        await context.bot.approve_chat_join_request(
            request.chat.id,
            request.from_user.id
        )
        print(
            f"GREET: заявка {request.from_user.id} в чат "
            f"{request.chat.id} принята"
        )
    except Exception as e:
        print(
            "GREET ERROR: не удалось принять заявку "
            f"{request.from_user.id} | {repr(e)}"
        )


def _is_in_chat(status, is_member):
    if status in (
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR
    ):
        return True

    if status == ChatMember.RESTRICTED:
        return bool(is_member)

    return False


async def greet_on_membership_change(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    # Ловит ЛЮБОЙ способ попадания в чат одним и тем же событием:
    # прямое добавление, вступление по ссылке, одобрение заявки ботом
    # или вручную самим админом из Telegram — во всех случаях у
    # пользователя одинаково меняется статус членства.
    result = update.chat_member

    if result is None:
        return

    diff = result.difference()
    status_change = diff.get("status")

    if status_change is None:
        return

    old_status, new_status = status_change
    old_is_member, new_is_member = diff.get("is_member", (None, None))

    print(
        f"GREET: chat_member {result.new_chat_member.user.id} в чате "
        f"{result.chat.id}: {old_status} -> {new_status}"
    )

    was_in = _is_in_chat(old_status, old_is_member)
    is_in = _is_in_chat(new_status, new_is_member)

    if was_in or not is_in:
        return

    user = result.new_chat_member.user

    if user.is_bot:
        return

    chat = result.chat

    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=DEFAULT_GREET,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"GREET ERROR: {chat.id} | {repr(e)}")
