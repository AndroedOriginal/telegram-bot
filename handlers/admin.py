from telegram import Update
from telegram.ext import ContextTypes


async def admins_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message_text = update.message.text

    if "@admins" in message_text:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="<i>Отчёт отправлен</i>⁣⁣⁣⁣⁣⁣",
            parse_mode="HTML"
        )
