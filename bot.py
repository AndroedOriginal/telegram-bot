import os
import json
import asyncio

from telegram import Bot, Update

from handlers.schedule import setup_scheduler

from telegram.ext import (
    Application,
    MessageHandler,
    filters
)

from handlers.welcome import welcome_new_member

TOKEN = os.getenv("TOKEN")
application = Application.builder().token(TOKEN).build()

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
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            welcome_new_member
        )
    )
    
    await application.initialize()
    await application.start()

    print("Бот запущен!")


    await asyncio.Event().wait()


asyncio.run(main())
