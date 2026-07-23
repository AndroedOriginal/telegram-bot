import os
import json
import asyncio

from telegram import Bot

from handlers.schedule import setup_scheduler


TOKEN = os.getenv("TOKEN")

print("Проверка TOKEN:")
print(TOKEN)


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


    print("Бот запущен!")


    await asyncio.Event().wait()


asyncio.run(main())
