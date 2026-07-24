import json
import os

FILE = "warnings.json"


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


def get_warns(user_id):
    return warnings.get(str(user_id), 0)


def add_warn(user_id):
    uid = str(user_id)

    warnings[uid] = warnings.get(uid, 0) + 1

    save_warnings(warnings)

    return warnings[uid]


def remove_warn(user_id):
    uid = str(user_id)

    if uid not in warnings:
        return 0

    warnings[uid] -= 1

    if warnings[uid] <= 0:
        del warnings[uid]

    save_warnings(warnings)

    return warnings.get(uid, 0)
