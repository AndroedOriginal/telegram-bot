import json
import os

from utils.paths import data_path
from handlers.immunity_storage import is_immune

FILE = data_path("user_directory.json")

# Спец-значение "цели" команды модерации, означающее "все известные боту
# обычные участники чата" — см. resolve_target и get_everyone_ids.
EVERYONE = "everyone"


def _load():
    if not os.path.exists(FILE):
        return {}

    try:
        with open(FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )


# username (lower-case, без @) -> user_id.
# Telegram Bot API не даёт надёжного способа найти произвольного
# пользователя по @username, поэтому бот запоминает всех, кого видел
# в чате, и ищет по этому локальному справочнику.
_directory = _load()


def remember_user(user):
    if user is None or not user.username:
        return

    username = user.username.lower()

    if _directory.get(username) != user.id:
        _directory[username] = user.id
        _save(_directory)


def get_id_by_username(username):
    return _directory.get(username.lower())


def get_all_known_ids():
    """Все ID пользователей, которых бот когда-либо видел (запомнил по @username)."""
    return set(_directory.values())


async def get_everyone_ids(context, chat_id, admin_ids, exclude_immune=True):
    """
    Возвращает ID всех обычных участников чата, которых бот знает по
    локальному справочнику user_directory и которые сейчас реально
    состоят в чате. Админы всегда исключены — "@everyone" в командах
    модерации на них не действует. По умолчанию исключены и обладатели
    иммунитета (exclude_immune=False — для снятия ограничений, где
    иммунитет не должен быть препятствием).

    Т.к. Bot API не даёт способа перечислить всех участников чата,
    список ограничен теми, кого бот хотя бы раз видел пишущим — как и
    везде в этом боте при поиске цели по @username.
    """
    result = set()

    for user_id in get_all_known_ids():
        if user_id in admin_ids:
            continue

        if exclude_immune and is_immune(chat_id, user_id):
            continue

        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
        except Exception:
            continue

        if member.status in ("left", "kicked") or member.user.is_bot:
            continue

        result.add(user_id)

    return result


async def remember_message_sender(
    update,
    context
):
    remember_user(update.effective_user)


async def resolve_target(update, context, admin_ids):
    """
    Определяет пользователя, на которого должна сработать команда
    модерации. Поддерживает три способа:

    1. Ответ на сообщение пользователя (как раньше).
    2. @username — ищется в локальном справочнике увиденных пользователей.
    3. Числовой ID пользователя.

    Возвращает (user_id, display_name, remaining_args, error).
    Если пользователь не определён, user_id будет None, а error —
    готовый текст, который можно отправить администратору.

    Отдельно поддерживается "@everyone"/"everyone" первым аргументом —
    тогда user_id будет равен EVERYONE, а вызывающая команда должна
    сама решить, как применить действие ко всем участникам сразу
    (см. get_everyone_ids). Проверяется раньше ответа на сообщение,
    чтобы явное "@everyone" не терялось, если команду случайно
    отправили ответом на чьё-то сообщение.
    """

    message = update.message
    args = list(context.args) if context.args else []

    if args and args[0].lower() in ("@everyone", "everyone"):
        return EVERYONE, "everyone", args[1:], None

    if message.reply_to_message:
        target = message.reply_to_message.from_user
        remember_user(target)

        return (
            target.id,
            target.username or target.first_name,
            args,
            None
        )

    usage_error = (
        "Используй команду ответом на сообщение пользователя "
        "либо укажи @username или ID пользователя."
    )

    if not args:
        return None, None, [], usage_error

    first = args[0]

    if first.startswith("@"):
        username = first[1:]
        user_id = get_id_by_username(username)

        if user_id is None:
            return (
                None,
                None,
                [],
                f"Не знаю пользователя @{username} — он должен хотя бы "
                "раз написать в чат, чтобы бот его запомнил. Либо "
                "используй команду ответом на его сообщение."
            )

        return user_id, username, args[1:], None

    if first.lstrip("-").isdigit():
        return int(first), first, args[1:], None

    return None, None, [], usage_error
