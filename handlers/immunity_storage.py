import json
import os
from datetime import datetime, timezone

from utils.paths import data_path

FILE = data_path("immunity.json")


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


# Иммунитет, как и варны, считается отдельно в каждом чате, а не глобально.
_immunity = _load()


def _key(chat_id, user_id):
    return f"{chat_id}_{user_id}"


def set_immunity(chat_id, user_id, until):
    """
    Выдаёт иммунитет. until — aware datetime (UTC) для временного
    иммунитета либо None для иммунитета навсегда.
    """
    key = _key(chat_id, user_id)

    _immunity[key] = {
        "until": until.isoformat() if until else None
    }

    _save(_immunity)


def remove_immunity(chat_id, user_id):
    key = _key(chat_id, user_id)

    if key in _immunity:
        del _immunity[key]
        _save(_immunity)


def is_immune(chat_id, user_id):
    """
    True, если у пользователя сейчас активен иммунитет. ВАЖНО: иммунитет
    определяется только по этому хранилищу, а не по декоративному
    тегу "⛨" — тег можно потерять/сменить вручную, а иммунитет от этого
    не должен пропадать (и наоборот, наличие тега само по себе не
    даёт иммунитета).

    Просроченный временный иммунитет автоматически убирается из
    хранилища при первой же проверке.
    """
    key = _key(chat_id, user_id)
    entry = _immunity.get(key)

    if entry is None:
        return False

    until = entry.get("until")

    if until is None:
        return True

    if datetime.fromisoformat(until) > datetime.now(timezone.utc):
        return True

    del _immunity[key]
    _save(_immunity)

    return False
