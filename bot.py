import os
import json
import asyncio

from telegram import Bot, Update

from handlers.schedule import setup_scheduler

from telegram.ext import (
Application,
MessageHandler,
CommandHandler,
CallbackQueryHandler,
filters
)

from handlers.admin import admins_command

from handlers.welcome import welcome_new_member

from handlers.warn import warn_command, cancel_warn

from handlers.unmute import unmute_command

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise Exception("TOKEN не найден в Variables")

from telegram.request import HTTPXRequest

from handlers.rules import rules_command

from handlers.msg import msg_command

from handlers.ban import ban_command, unban_callback

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

bot = Bot(TOKEN)


async def send_message(text):
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=text,
            parse_mode="HTML"
        )

        print("Сообщение отправлено:", text)

    except Exception as e:
        print("Ошибка отправки:", repr(e))


async def main():

    print("УНИКАЛЬНЫЙ ЗАПУСК БОТА")


    scheduler = setup_scheduler(
        config,
        send_message
    )


    scheduler.start()


    application.add_handler(
        CommandHandler(
            "warn",
            warn_command
        )
    )
    
    
    application.add_handler(
        CallbackQueryHandler(
            cancel_warn,
            pattern="^cancel_warn_"
        )
    )
    
    
    application.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            welcome_new_member
        )
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
            pattern="unban"
        )
    )
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    print("Бот запущен!")

    try:
        await asyncio.Event().wait()
    
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


asyncio.run(main())
