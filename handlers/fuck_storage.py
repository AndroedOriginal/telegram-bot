import json
import os
from datetime import datetime, timezone

from utils.paths import data_path

FILE = data_path("fuck_toggle.json")


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


# По умолчанию /fuck выключен в любом чате, пока владелец чата явно
# не включит его командой "fuck on"/"fuck on <время>".
_toggle = _load()


def _key(chat_id):
    return str(chat_id)


def set_fuck_toggle(chat_id, until):
    """
    until — aware datetime (UTC) для временного включения либо None
    для включения навсегда.
    """
    _toggle[_key(chat_id)] = {
        "until": until.isoformat() if until else None
    }

    _save(_toggle)


def disable_fuck(chat_id):
    key = _key(chat_id)

    if key in _toggle:
        del _toggle[key]
        _save(_toggle)


def is_fuck_enabled(chat_id):
    """
    True, если /fuck сейчас включён в чате явным тумблером владельца.
    Просроченное временное включение автоматически убирается из
    хранилища. Логика "нюдсочетверга" (доступ по дням недели) живёт
    отдельно в handlers/fuck.py и сюда не относится.
    """
    key = _key(chat_id)
    entry = _toggle.get(key)

    if entry is None:
        return False

    until = entry.get("until")

    if until is None:
        return True

    if datetime.fromisoformat(until) > datetime.now(timezone.utc):
        return True

    del _toggle[key]
    _save(_toggle)

    return False
