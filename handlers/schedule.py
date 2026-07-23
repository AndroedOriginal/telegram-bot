import pytz

from apscheduler.schedulers.asyncio import AsyncIOScheduler


timezone = pytz.timezone("Europe/Moscow")


def setup_scheduler(config, send_message):
    scheduler = AsyncIOScheduler(
        timezone=timezone
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
            args=[message["text"]],
            id=f"message_{message['time']}",
            replace_existing=True
        )

        print(
            f"Добавлено задание: {message['time']} -> {message['text']}"
        )

    return scheduler
