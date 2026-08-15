import os

from telegram import Update

from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    ChatJoinRequestHandler,
    filters
)

from telegram.request import HTTPXRequest

from handlers.events import (
    init_events,
    addevent_command,
    setevent_command,
    delevent_command,
    launchevent_command,
    events_command,
    on_bot_added_to_chat
)
from handlers.admin import admins_command
from handlers.antispam import (
    check_spam,
    antispam_command,
    antirepeat_command
)
from handlers.greet import (
    greet_command,
    greet_new_members,
    track_join_request
)
from handlers.warn import warn_command, cancel_warn, unwarn_command
from handlers.unmute import unmute_command
from handlers.rules import rules_command
from handlers.msg import msg_command
from handlers.ban import ban_command, unban_callback, unban_command
from handlers.mute import mute_command, cancel_mute_callback
from handlers.immunity import immunity_command, cancel_immunity_callback
from handlers.fuck import fuck_command
from handlers.nudesday import nudesday_command, init_nudesday
from handlers.plots import addplot_command, setplot_command, delplot_command
from handlers.owner import owner_command
from utils.targeting import remember_message_sender
from utils.permissions import on_chat_member_changed


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


# Заявки не одобряются сами по себе — только запоминаются, пока админ
# не впустит их через /greet.
application.add_handler(
    ChatJoinRequestHandler(track_join_request)
)


# Приветствуем сразу после служебного сообщения "X присоединился" —
# оно появляется и при прямом добавлении, и при одобрении заявки
# (ботом или вручную самим админом), так что порядок "вход -> приветствие"
# гарантирован.
application.add_handler(
    MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        greet_new_members
    )
)


application.add_handler(
    CommandHandler(
        "greet",
        greet_command
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


# Отдельная группа, чтобы antispam проверял каждое сообщение независимо
# от remember_message_sender и обычных командных хендлеров.
application.add_handler(
    MessageHandler(
        filters.ALL,
        check_spam
    ),
    group=2
)


application.add_handler(
    CommandHandler(
        "antispam",
        antispam_command
    )
)


application.add_handler(
    CommandHandler(
        "antirepeat",
        antirepeat_command
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
        "immunity",
        immunity_command
    )
)


application.add_handler(
    CallbackQueryHandler(
        cancel_immunity_callback,
        pattern=r"^cancel_immunity_"
    )
)


application.add_handler(
    CallbackQueryHandler(
        cancel_mute_callback,
        pattern=r"^cancel_mute_"
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
        "fuck",
        fuck_command
    )
)


application.add_handler(
    CommandHandler(
        "nudesday",
        nudesday_command
    )
)


application.add_handler(
    CommandHandler(
        "addplot",
        addplot_command
    )
)


application.add_handler(
    CommandHandler(
        "setplot",
        setplot_command
    )
)


application.add_handler(
    CommandHandler(
        "delplot",
        delplot_command
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
        "launchevent",
        launchevent_command
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


# Сбрасываем кэш админов сразу при изменении прав/тега любого участника —
# иначе antispam может до минуты считать свежего админа обычным юзером.
application.add_handler(
    ChatMemberHandler(
        on_chat_member_changed,
        ChatMemberHandler.CHAT_MEMBER
    )
)


async def start_scheduler(app):
    # AsyncIOScheduler.start() требует уже запущенный event loop,
    # поэтому запускаем его тут, а не на верхнем уровне модуля.
    init_events(app.bot)
    init_nudesday(app.bot)


application.post_init = start_scheduler


print("УНИКАЛЬНЫЙ ЗАПУСК БОТА")

# Без явного allowed_updates Telegram НЕ присылает chat_member и
# chat_join_request, даже если хендлеры на них зарегистрированы —
# из-за этого /greet не одобрял заявки на вступление.
application.run_polling(
    drop_pending_updates=False,
    allowed_updates=Update.ALL_TYPES
)
