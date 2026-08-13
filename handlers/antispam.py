import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import ContextTypes

from handlers.mute import MUTE_PERMISSIONS
from handlers.storage import add_warn
from utils.permissions import is_chat_admin


BURST_WINDOW = 3        # секунд
BURST_LIMIT = 10        # сообщений

REPEAT_WINDOW = 60       # секунд
REPEAT_LIMIT = 10        # одинаковых сообщений либо стикеров/гифок

# (chat_id, user_id) -> deque[(timestamp, text_or_none, is_sticker_or_gif)].
# Только в памяти процесса — это защита от флуда в реальном времени,
# хранить историю сообщений на диске смысла нет.
_history = defaultdict(deque)


def _prune(entries, now):
    # REPEAT_WINDOW шире BURST_WINDOW, поэтому одной чистки по нему
    # достаточно для обоих правил.
    while entries and now - entries[0][0] > REPEAT_WINDOW:
        entries.popleft()


async def _punish(context, chat_id, user_id, minutes, warn):
    until_date = datetime.now(timezone.utc) + timedelta(minutes=minutes)

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=MUTE_PERMISSIONS,
            until_date=until_date
        )
    except Exception as e:
        print(f"ANTISPAM ERROR: мут {user_id} в {chat_id} | {repr(e)}")
        return

    if warn:
        add_warn(chat_id, user_id)

    reason = "флуд" if warn else "повторяющиеся сообщения"

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🔇 Пользователь [{user_id}] замучен на {minutes} мин. "
                f"за {reason}."
            )
        )
    except Exception as e:
        print(f"ANTISPAM ERROR: {chat_id} | {repr(e)}")

    print(
        f"ANTISPAM: {user_id} в {chat_id} замучен на {minutes}м "
        f"({reason})"
    )


async def check_spam(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if message is None or user is None or user.is_bot:
        return

    if chat.type not in ("group", "supergroup"):
        return

    if await is_chat_admin(update, context):
        return

    now = time.monotonic()
    key = (chat.id, user.id)
    entries = _history[key]

    is_sticker_or_gif = bool(message.sticker or message.animation)
    text = (message.text or message.caption or "").strip() or None

    entries.append((now, text, is_sticker_or_gif))
    _prune(entries, now)

    # ===== Правило 1: 10+ сообщений за 3 секунды -> мут 1м + варн =====

    burst_count = sum(
        1 for ts, _, _ in entries if now - ts <= BURST_WINDOW
    )

    if burst_count >= BURST_LIMIT:
        entries.clear()
        await _punish(context, chat.id, user.id, minutes=1, warn=True)
        return

    # ===== Правило 2: 10+ одинаковых сообщений либо стикеров/гифок =====
    # ===== за 1 минуту -> мут 10м =====

    media_count = sum(1 for _, _, is_media in entries if is_media)

    if media_count >= REPEAT_LIMIT:
        entries.clear()
        await _punish(context, chat.id, user.id, minutes=10, warn=False)
        return

    if text is not None:
        same_text_count = sum(1 for _, t, _ in entries if t == text)

        if same_text_count >= REPEAT_LIMIT:
            entries.clear()
            await _punish(context, chat.id, user.id, minutes=10, warn=False)
