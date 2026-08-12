import os

from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    filters
)

from telegram.request import HTTPXRequest

from handlers.events import (
    init_events,
    addevent_command,
    setevent_command,
    delevent_command,
    events_command,
    on_bot_added_to_chat
)
from handlers.admin import admins_command
from handlers.welcome import welcome_new_member
from handlers.warn import warn_command, cancel_warn, unwarn_command
from handlers.unmute import unmute_command
from handlers.rules import rules_command
from handlers.msg import msg_command
from handlers.ban import ban_command, unban_callback, unban_command
from handlers.mute import mute_command
from handlers.owner import owner_command
from utils.targeting import remember_message_sender


TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise Exception("TOKEN не найден в Variables")


request = HTTPXRequest(
    connect_timeout=30,
    read_timeout=30,
    write_timeout=30,
    pool_timeout=30
)


application = (
    Application.builder()
    .token(TOKEN)
    .request(request)
    .build()
)


print("TOKEN найден:", TOKEN is not None)


application.add_handler(
    CommandHandler(
        "warn",
        warn_command
    )
)


application.add_handler(
    CallbackQueryHandler(
        cancel_warn,
        pattern=r"^cancel_warn_"
    )
)


application.add_handler(
    MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        welcome_new_member
    )
)


# Запоминаем всех, кто пишет в чат, чтобы команды модерации можно было
# использовать по @username, а не только ответом на сообщение.
# group=1, чтобы не мешать остальным обработчикам в группе 0.
application.add_handler(
    MessageHandler(
        filters.ALL,
        remember_message_sender
    ),
    group=1
)


application.add_handler(
    MessageHandler(
        filters.TEXT & filters.Regex("@admins"),
        admins_command
    )
)


application.add_handler(
    CommandHandler(
        "unmute",
        unmute_command
    )
)


application.add_handler(
    CommandHandler(
        "rules",
        rules_command
    )
)


application.add_handler(
    CommandHandler(
        "send",
        msg_command
    )
)


application.add_handler(
    CommandHandler(
        "ban",
        ban_command
    )
)


application.add_handler(
    CallbackQueryHandler(
        unban_callback,
        pattern=r"^unban"
    )
)


application.add_handler(
    CommandHandler(
        "unban",
        unban_command
    )
)


application.add_handler(
    CommandHandler(
        "unwarn",
        unwarn_command
    )
)


application.add_handler(
    CommandHandler(
        "mute",
        mute_command
    )
)


application.add_handler(
    CommandHandler(
        "owner",
        owner_command
    )
)


application.add_handler(
    CommandHandler(
        "addevent",
        addevent_command
    )
)


application.add_handler(
    CommandHandler(
        "setevent",
        setevent_command
    )
)


application.add_handler(
    CommandHandler(
        "delevent",
        delevent_command
    )
)


application.add_handler(
    CommandHandler(
        "events",
        events_command
    )
)


# Ловим момент, когда бота добавляют в новый чат, чтобы сразу
# завести для него 3 базовых события.
application.add_handler(
    ChatMemberHandler(
        on_bot_added_to_chat,
        ChatMemberHandler.MY_CHAT_MEMBER
    )
)


async def start_scheduler(app):
    # AsyncIOScheduler.start() требует уже запущенный event loop,
    # поэтому запускаем его тут, а не на верхнем уровне модуля.
    init_events(app.bot)


application.post_init = start_scheduler


print("УНИКАЛЬНЫЙ ЗАПУСК БОТА")

application.run_polling(
    drop_pending_updates=False
)
