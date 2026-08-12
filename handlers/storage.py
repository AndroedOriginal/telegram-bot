import json
import os

from utils.paths import data_path

FILE = data_path("warnings.json")


def load_warnings():
    if not os.path.exists(FILE):
        return {}

    try:
        with open(FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_warnings(data):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )


warnings = load_warnings()


def _key(chat_id, user_id):
    # Варны считаются отдельно в каждом чате, а не глобально по всем чатам,
    # где состоит бот.
    return f"{chat_id}_{user_id}"


def get_warns(chat_id, user_id):
    return warnings.get(_key(chat_id, user_id), 0)


def add_warn(chat_id, user_id):
    key = _key(chat_id, user_id)

    warnings[key] = warnings.get(key, 0) + 1

    save_warnings(warnings)

    return warnings[key]


def remove_warn(chat_id, user_id):
    key = _key(chat_id, user_id)

    if key not in warnings:
        return 0

    warnings[key] -= 1

    if warnings[key] <= 0:
        del warnings[key]

    save_warnings(warnings)

    return warnings.get(key, 0)


def reset_warn(chat_id, user_id):
    key = _key(chat_id, user_id)

    if key in warnings:
        del warnings[key]

    save_warnings(warnings)
