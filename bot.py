import os
import json

from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters
)

from telegram.request import HTTPXRequest

from handlers.schedule import setup_scheduler
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


with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)


CHAT_ID = config["chat_id"]


async def send_message(text):

    try:

        await application.bot.send_message(
            chat_id=CHAT_ID,
            text=text,
            parse_mode="HTML"
        )

        print("Сообщение отправлено:", text)

    except Exception as e:

        print(
            "Ошибка отправки:",
            repr(e)
        )


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


scheduler = setup_scheduler(
    config,
    send_message
)


async def start_scheduler(app):
    # AsyncIOScheduler.start() требует уже запущенный event loop,
    # поэтому запускаем его тут, а не на верхнем уровне модуля.
    scheduler.start()
    print("Планировщик запущен")


application.post_init = start_scheduler


print("УНИКАЛЬНЫЙ ЗАПУСК БОТА")

application.run_polling(
    drop_pending_updates=False
)
