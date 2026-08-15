import json

from telegram import Update
from telegram.ext import ContextTypes

from html import escape

from handlers.owner import OWNER_ID
from handlers.plots_storage import add_plot, set_plot, delete_plot, get_all_plots


async def _delete_and_check_owner(update):
    """
    Библиотека сценариев общая для всех чатов бота, поэтому управлять ей
    может только владелец бота (OWNER_ID), а не админы отдельных чатов.
    """
    message = update.effective_message

    try:
        await message.delete()
    except Exception:
        pass

    return update.effective_user.id == OWNER_ID


def _parse_name_and_list(text, command):
    """
    Разбирает "/addplot имя [\"строка 1\", \"строка 2\"]" на
    (имя, [строки]). Возвращает (None, None), если формат неверный.
    """
    prefix = f"/{command}"

    if text.startswith(prefix):
        text = text[len(prefix):].strip()

    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        return None, None

    name, raw_list = parts

    try:
        lines = json.loads(raw_list)
    except Exception:
        return None, None

    if not isinstance(lines, list) or not lines:
        return None, None

    if not all(isinstance(line, str) for line in lines):
        return None, None

    return name, lines


async def addplot_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat = update.effective_chat

    if not await _delete_and_check_owner(update):
        return

    name, lines = _parse_name_and_list(
        update.effective_message.text, "addplot"
    )

    if name is None:
        await chat.send_message(
            'Используй: /addplot имя ["строка 1", "строка 2"]'
        )
        return

    if name.lower() in get_all_plots():
        await chat.send_message(
            f"Сценарий «{escape(name)}» уже существует. Используй "
            "/setplot, чтобы изменить его."
        )
        return

    add_plot(name, lines)

    await chat.send_message(
        f"Сценарий «{escape(name)}» добавлен ({len(lines)} сообщ.)."
    )


async def setplot_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat = update.effective_chat

    if not await _delete_and_check_owner(update):
        return

    name, lines = _parse_name_and_list(
        update.effective_message.text, "setplot"
    )

    if name is None:
        await chat.send_message(
            'Используй: /setplot имя ["строка 1", "строка 2"]'
        )
        return

    if name.lower() not in get_all_plots():
        await chat.send_message(
            f"Сценарий «{escape(name)}» не найден. Используй /addplot, "
            "чтобы создать новый."
        )
        return

    set_plot(name, lines)

    await chat.send_message(
        f"Сценарий «{escape(name)}» изменён ({len(lines)} сообщ.)."
    )


async def delplot_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat = update.effective_chat

    if not await _delete_and_check_owner(update):
        return

    args = context.args

    if not args:
        await chat.send_message("Используй: /delplot имя")
        return

    name = args[0]

    if not delete_plot(name):
        await chat.send_message(f"Сценарий «{escape(name)}» не найден.")
        return

    await chat.send_message(f"Сценарий «{escape(name)}» удалён.")
