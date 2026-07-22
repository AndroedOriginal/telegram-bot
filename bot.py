import json
import pytz
import asyncio

from telegram import Bot
from apscheduler.schedulers.blocking import BlockingScheduler


TOKEN = "8852234267:AAFjbDRdfejts4NyJogTqjoYb1cuD12nDkU"


with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)


CHAT_ID = config["chat_id"]

bot = Bot(TOKEN)
asyncio.run(
    bot.send_message(
        chat_id=CHAT_ID,
        text="🚀 Тест при запуске"
    )
)
print("Тестовое сообщение отправлено")

timezone = pytz.timezone("Europe/Moscow")

scheduler = BlockingScheduler(timezone=timezone)


def send_message(text):
    try:
        asyncio.run(
            bot.send_message(
                chat_id=CHAT_ID,
                text=text
            )
        )
        print("Сообщение отправлено!")
    except Exception as e:
        print(f"Ошибка: {e}")


for message in config["messages"]:

    hour, minute = map(
        int,
        message["time"].split(":")
    )
    print(f"Добавлено задание: {message['time']} -> {message['text']}")
    scheduler.add_job(
        send_message,
        "cron",
        hour=hour,
        minute=minute,
        args=[message["text"]]
    )


print("Бот запущен!")
print(scheduler.get_jobs())
scheduler.start()
