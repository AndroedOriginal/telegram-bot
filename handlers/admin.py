from telegram import Update
from telegram.ext import ContextTypes


async def admins_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if "@admins" in update.message.text:
        await update.message.reply_text(
            "*Отчёт отправлен*⁣⁣⁣⁣⁣⁣",
            parse_mode="Markdown"
        )
