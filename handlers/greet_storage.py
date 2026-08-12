import json
import os

from utils.paths import data_path

FILE = data_path("greet.json")

# Прежний статичный текст приветствия — используется по умолчанию, пока
# админ не задаст свой через /greet.
DEFAULT_GREET = (
    "Добро пожаловать в Нюберг чат!\n\n"
    "Место, где ты можешь пообщаться на любые темы, поделиться хорошей "
    "музыкой и посоревноваться с другими участниками в играх.\n\n"
    "Не забудь прочитать "
    "<a href=\"https://telegra.ph/Pravila-Nyuberg-CHata-12-03-2\">"
    "правила</a> чата, перед началом общения, говорят, тут строгая "
    "модерация 👀"
)


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


_greet = _load()


def get_greet(chat_id):
    return _greet.get(str(chat_id), DEFAULT_GREET)


def set_greet(chat_id, text):
    _greet[str(chat_id)] = text
    _save(_greet)


def reset_greet(chat_id):
    key = str(chat_id)

    if key in _greet:
        del _greet[key]
        _save(_greet)
