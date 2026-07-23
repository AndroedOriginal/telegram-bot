from telegram import Update
from telegram.ext import ContextTypes


async def admins_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.message.from_user.is_bot:
        return

    text = update.message.text.lower()

    if "@admins" in text:

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="<i>Отчёт отправлен</i>",
            parse_mode="HTML"
        )
