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


# chat_id (str) -> bool. По умолчанию (запись отсутствует) — выключено.
_settings = _load()


def is_nudesday_enabled(chat_id):
    return bool(_settings.get(str(chat_id)))


def set_nudesday_enabled(chat_id, enabled):
    _settings[str(chat_id)] = enabled
    _save(_settings)


def get_all_nudesday_chats():
    return [
        int(chat_id) for chat_id, enabled in _settings.items() if enabled
    ]
