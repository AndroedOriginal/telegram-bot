import json
import os
from datetime import datetime, timezone

from utils.paths import data_path

FILE = data_path("fuck.json")


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


# chat_id (str) -> {"enabled": bool, "until": iso-строка или None}.
# По умолчанию (запись отсутствует) — команда выключена.
_settings = _load()


def _key(chat_id):
    return str(chat_id)


def set_fuck_enabled(chat_id, until=None):
    """
    until — aware datetime (UTC) для временного включения либо None
    для включения навсегда.
    """
    _settings[_key(chat_id)] = {
        "enabled": True,
        "until": until.isoformat() if until else None
    }

    _save(_settings)


def set_fuck_disabled(chat_id):
    _settings[_key(chat_id)] = {"enabled": False, "until": None}
    _save(_settings)


def is_fuck_enabled(chat_id):
    """
    True, если команда сейчас включена в этом чате (навсегда либо в
    рамках ещё не истёкшего временного окна). Истёкшее временное окно
    автоматически выключает команду при первой же проверке.
    """
    entry = _settings.get(_key(chat_id))

    if entry is None or not entry.get("enabled"):
        return False

    until = entry.get("until")

    if until is None:
        return True

    if datetime.fromisoformat(until) > datetime.now(timezone.utc):
        return True

    _settings[_key(chat_id)] = {"enabled": False, "until": None}
    _save(_settings)

    return False
