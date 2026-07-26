from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from datetime import timedelta


def parse_time(value):

    try:
        if value.endswith("m"):
            return timedelta(
                minutes=int(value[:-1])
            )

        if value.endswith("h"):
            return timedelta(
                hours=int(value[:-1])
            )

        if value.endswith("d"):
            return timedelta(
                days=int(value[:-1])
            )

    except:
        pass

    return None



async def mute_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message
    chat = update.effective_chat


    # проверка админа

    admins = await context.bot.get_chat_administrators(
        chat.id
    )

    admin_ids = [
        admin.user.id
        for admin in admins
    ]


    if update.effective_user.id not in admin_ids:
        try:
            await message.delete()
        except:
            pass
        return



    # ответ на сообщение

    if not message.reply_to_message:
        await message.delete()
        return



    user = message.reply_to_message.from_user



    # нельзя мутить админа

    if user.id in admin_ids:
        await message.delete()

        print(
            f"MUTE BLOCKED: {user.id} is admin"
        )

        return



    # время

    if not context.args:
        await message.delete()
        return


    duration = parse_time(
        context.args[0]
    )


    if not duration:
        await message.delete()
        return



    # выдаём мут

    await context.bot.restrict_chat_member(
        chat_id=chat.id,
        user_id=user.id,

        permissions=ChatPermissions(
            can_send_messages=False
        ),

        until_date=duration
    )



    # удаляем команду

    try:
        await message.delete()
    except:
        pass



    print(
        f"MUTE: {user.id} на {duration}"
    )
