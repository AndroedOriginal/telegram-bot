import json
import os
import random

from utils.paths import data_path

FILE = data_path("plots.json")


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


# Общая для ВСЕХ чатов библиотека сценариев для /fuck — каждый сценарий
# это список сообщений, которые бот шлёт одно за другим. Не привязана
# к конкретному чату: управляется только владельцем бота (см. handlers/plots.py).
_plots = _load()

# Заглушка-инструкция, а не настоящая шутка — никогда не запускается,
# ни случайно, ни явно по имени.
_EXCLUDED_PLOTS = {"example"}


def add_plot(name, lines):
    _plots[name.lower()] = list(lines)
    _save(_plots)


def set_plot(name, lines):
    add_plot(name, lines)


def delete_plot(name):
    key = name.lower()

    if key not in _plots:
        return False

    del _plots[key]
    _save(_plots)

    return True


def get_plot(name):
    key = name.lower()

    if key in _EXCLUDED_PLOTS:
        return None

    return _plots.get(key)


def get_all_plots():
    return _plots


def get_random_plot():
    candidates = [
        lines for name, lines in _plots.items()
        if name not in _EXCLUDED_PLOTS
    ]

    if not candidates:
        return None

    return random.choice(candidates)
