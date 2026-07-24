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

    print("ДОБАВЛЯЕМ ВАРН:", uid)

    data = load_warnings()

    data[uid] = data.get(uid, 0) + 1

    print("НОВЫЕ ДАННЫЕ:", data)

    save_warnings(data)

    print("ФАЙЛ СОХРАНЕН")

    return data[uid]


def remove_warn(user_id):
    uid = str(user_id)

    data = load_warnings()

    if uid not in data:
        return 0

    data[uid] -= 1

    if data[uid] <= 0:
        del data[uid]

    save_warnings(data)

    return data.get(uid, 0)
