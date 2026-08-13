import re

# Секунды в каждой единице — используется и /mute, и настройками antispam/
# antirepeat, чтобы не дублировать парсинг в каждом файле.
_UNIT_SECONDS = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
    "y": 86400 * 365,
}

_PATTERN = re.compile(r"^(\d+)(s|m|h|d|y)$")


def parse_duration_seconds(text):
    """
    Разбирает строку вида "30s", "2m", "1h", "3d", "1y" в количество
    секунд. Возвращает None, если формат неверный или число <= 0.
    """
    if not text:
        return None

    match = _PATTERN.fullmatch(text.strip().lower())

    if not match or int(match.group(1)) <= 0:
        return None

    value = int(match.group(1))
    unit = match.group(2)

    return value * _UNIT_SECONDS[unit]
