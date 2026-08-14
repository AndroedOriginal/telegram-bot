import json
import os

from utils.paths import data_path

FILE = data_path("antispam.json")

# "burst" — правило флуда (N+ сообщений за окно времени).
# "repeat" — правило повторов (N+ одинаковых сообщений либо стикеров/гифок
# за окно времени).
DEFAULT_BURST = {"enabled": True, "window": 3, "limit": 10}
DEFAULT_REPEAT = {"enabled": True, "window": 60, "limit": 10}


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


# Настройки — на чат, поэтому у каждого чата бота своя чувствительность
# antispam/antirepeat.
_settings = _load()


def _chat_key(chat_id):
    return str(chat_id)


def get_burst_settings(chat_id):
    chat = _settings.get(_chat_key(chat_id), {})
    return {**DEFAULT_BURST, **chat.get("burst", {})}


def get_repeat_settings(chat_id):
    chat = _settings.get(_chat_key(chat_id), {})
    return {**DEFAULT_REPEAT, **chat.get("repeat", {})}


def _set_rule(rule_name, defaults, chat_id, enabled, window, limit):
    key = _chat_key(chat_id)
    chat = _settings.setdefault(key, {})
    rule = {**defaults, **chat.get(rule_name, {})}

    rule["enabled"] = enabled

    if window is not None:
        rule["window"] = window

    if limit is not None:
        rule["limit"] = limit

    chat[rule_name] = rule
    _save(_settings)

    return rule


def set_burst_settings(chat_id, enabled, window=None, limit=None):
    return _set_rule(
        "burst", DEFAULT_BURST, chat_id, enabled, window, limit
    )


def set_repeat_settings(chat_id, enabled, window=None, limit=None):
    return _set_rule(
        "repeat", DEFAULT_REPEAT, chat_id, enabled, window, limit
    )
