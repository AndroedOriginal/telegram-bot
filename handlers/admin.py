from telegram import Update
from telegram.ext import ContextTypes


async def admins_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "<i>Отчёт отправлен</i>",
        parse_mode="HTML"
    )
