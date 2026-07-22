import json
import pytz

from telegram import Bot
from apscheduler.schedulers.blocking import BlockingScheduler


TOKEN = "8975007106:AAHhehyrQB-0-Xty9aNB59t-u78kAmgxEAw"


# Загружаем настройки
with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)


CHAT_ID = config["chat_id"]

bot = Bot(TOKEN)

timezone = pytz.timezone("Europe/Moscow")

scheduler = BlockingScheduler(
    timezone=timezone
)


def send_message(text):
    bot.send_message(
        chat_id=CHAT_ID,
        text=text
    )


# Создаем расписание
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
        args=[
            message["text"]
        ]
    )


print("Бот запущен!")

scheduler.start()
