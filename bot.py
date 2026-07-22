import os
import json
import asyncio
import pytz

from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler


TOKEN = "8852234267:AAFjbDRdfejts4NyJogTqjoYb1cuD12nDkU"


with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)


CHAT_ID = config["chat_id"]

bot = Bot(TOKEN)

timezone = pytz.timezone("Europe/Moscow")

scheduler = AsyncIOScheduler(
    timezone=timezone
)


async def send_message(text):
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=text
        )

        print("Сообщение отправлено:", text)

    except Exception as e:
        print("Ошибка отправки:", repr(e))


async def main():

    for message in config["messages"]:

        hour, minute = map(
            int,
            message["time"].split(":")
        )

        scheduler.add_job(
            send_message,
            "cron",
            hour=hour,
            minute=minute,
            args=[message["text"]],
            id=f"message_{message['time']}",
            replace_existing=True
        )

        print(
            f"Добавлено задание: {message['time']} -> {message['text']}"
        )


    scheduler.start()

    print("Бот запущен!")

    # чтобы программа не завершилась
    await asyncio.Event().wait()


asyncio.run(main())
