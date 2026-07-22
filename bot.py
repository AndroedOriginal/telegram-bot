import json
import pytz
import asyncio

from telegram import Bot
from apscheduler.schedulers.blocking import BlockingScheduler


TOKEN = "8852234267:AAE9gojlSr--nqrnHk3WYOBPly2TjUch-uw"


with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)


CHAT_ID = config["chat_id"]

bot = Bot(TOKEN)

timezone = pytz.timezone("Europe/Moscow")

scheduler = BlockingScheduler(timezone=timezone)


def send_message(text):
    asyncio.run(
        bot.send_message(
            chat_id=CHAT_ID,
            text=text
        )
    )


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
        args=[message["text"]]
    )


print("Бот запущен!")

scheduler.start()
