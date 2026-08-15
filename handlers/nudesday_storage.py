import json
import os

from utils.paths import data_path

FILE = data_path("nudesday.json")


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


# chat_id (str) -> bool. Выключен по умолчанию в любом чате.
_settings = _load()


def _key(chat_id):
    return str(chat_id)


def set_nudesday(chat_id, enabled):
    _settings[_key(chat_id)] = bool(enabled)
    _save(_settings)


def is_nudesday_enabled(chat_id):
    return bool(_settings.get(_key(chat_id), False))


def get_enabled_chats():
    return [key for key, enabled in _settings.items() if enabled]
