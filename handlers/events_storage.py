import json
import os

from utils.paths import data_path

FILE = data_path("events.json")


# Базовые события — включены по умолчанию для любого чата, пока
# админы не изменят их через /setevent или не удалят через /delevent.
DEFAULT_EVENTS = {
    "radio": {
        "time": "22:00",
        "text": (
            "ночное радио начинает свое вещание!\n\n"
            "правила такие: каждый желающий может отправить один и только "
            "один трек.\n\n"
            "<tg-spoiler>для отправки трека напишите в сообщении @LyBot и "
            "затем название трека. Так же можно использовать @mus_vir_bot "
            "для поиска по ВК Музыке, @Gozilla_bot для отправки аудио из "
            "ссылки с YouTube, @deezload2bot для отправки аудио по ссылке "
            "из Deezer или из Spotify, @scload_bot для отправки треков с "
            "SoundCloud.</tg-spoiler>"
        )
    },
    "photo": {
        "time": "21:30",
        "text": (
            "Объявляется Фотинг 📷 🖼\n\n"
            "Кидайте любые красивые, атмосферные и вайбовые фотографии — "
            "на любой вкус и цвет.\n\n"
            "Неважно, что это: городские улицы, природа, ночные огни, "
            "уют комнаты, дождь за окном или случайный удачный кадр.\n\n"
            "Красивых фоточек 🌏"
        )
    },
    "venting": {
        "time": "22:30",
        "text": (
            "Объявляется нытинг📢😫\n\n"
            "правила такие: каждый желающий может выговориться о том, что "
            "у него на душе. без страха быть осмеянным, непонятым или "
            "услышать, что «у других хуже».\n\n"
            "1. Каждый может ныть по любому поводу.\n"
            "2. Осуждать, высмеивать или обесценивать чужие переживания "
            "нельзя.\n"
            "3. Соблюдайте общие правила чата.\n"
            "4. Относитесь друг к другу с уважением и без оскорблений.\n\n"
            "иногда достаточно просто выговориться.\n\n"
            "удачного нытья😩"
        )
    }
}


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


# chat_id (str) -> { название события: {"time": "HH:MM", "text": "..."} }
_events = _load()


def get_chat_events(chat_id):
    """
    Возвращает события чата. Если чат встречается первый раз —
    заводит для него 3 базовых события по умолчанию.
    """
    key = str(chat_id)

    if key not in _events:
        _events[key] = {
            name: dict(event)
            for name, event in DEFAULT_EVENTS.items()
        }
        _save(_events)

    return _events[key]


def set_chat_event(chat_id, name, time_str, text):
    # get_chat_events гарантирует, что базовые события уже посеяны,
    # прежде чем мы что-то в них добавим/изменим.
    chat_events = get_chat_events(chat_id)

    chat_events[name.lower()] = {
        "time": time_str,
        "text": text
    }

    _save(_events)


def delete_chat_event(chat_id, name):
    chat_events = get_chat_events(chat_id)
    name = name.lower()

    if name not in chat_events:
        return False

    del chat_events[name]
    _save(_events)

    return True


def get_all_events():
    return _events
